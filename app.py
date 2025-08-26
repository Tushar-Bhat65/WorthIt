# app.py
# Fully revised, debug-heavy, full implementation.
# - Central Playwright manager (kept for compatibility)
# - Selenium concurrency control for background scrapers
# - Robust task->site tagging (no more "Unknown")
# - Per-scraper retries/timeouts with detailed logging
# - SSE UI embedded inline
# - Scrapers remain separate (under scrapers/)
# - ADDED: worthit_score function and integration

import argparse
import asyncio
import inspect
import json
import logging
import time
import traceback
from typing import Any, Dict, List, Callable, Optional, Tuple

import uvicorn
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, HTMLResponse, JSONResponse

# === IMPORT SCRAPERS (must match scrapers directory) ===
from scrapers.amazon import scrape_amazon
# MODIFICATION: Import only the function that now exists in flipkart.py
from scrapers.flipkart import fetch_flipkart_products
from scrapers.croma import get_cheapest_croma_product

# background scrapers (unchanged)
from scrapers.reliance import scrape_reliance_product
from scrapers.poorvika import get_cheapest_poorvika_product
from scrapers.pai import get_cheapest_pai_product
from scrapers.sangeetha import scrape_sangeetha_product

# Allow us to set module-level _manager if a scraper expects that name
import scrapers.amazon as amazon_mod
import scrapers.flipkart as flipkart_mod
import scrapers.croma as croma_mod

# ----------------------------------------------------------------
# Logging configuration (very verbose to help debugging)
# ----------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("app")
logger.info("Logger initialized for app module")

# ----------------------------------------------------------------
# FastAPI app and CORS
# ----------------------------------------------------------------
app = FastAPI(title="Price Compare — SSE")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # set specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# store background fetch task for /more keyed by lowercase query
# Each value will be an asyncio.Task that resolves to a dict mapping site->result
background_results: Dict[str, asyncio.Task] = {}

# Playwright run-time objects (populated on startup if Playwright available)
_playwright = None
_browser = None
_playwright_manager = None

# Limit concurrent Selenium usage (some scrapers use webdriver)
SELENIUM_CONCURRENCY = 4
selenium_semaphore = asyncio.Semaphore(SELENIUM_CONCURRENCY)

# ----------------------------------------------------------------
# Manager that exposes acquire_context() for scrapers that expect it.
# Not all of your scrapers use Playwright; it's safe to keep this in.
# ----------------------------------------------------------------
class PlaywrightManager:
    def __init__(self, browser, reuse_context: bool = False, max_concurrent_contexts: int = 4, debug_name: str = "PlayMgr"):
        self.browser = browser
        self.reuse_context = reuse_context
        self._shared_ctx = None
        self._debug_name = debug_name
        # control how many contexts are created concurrently to avoid resource storm
        self._ctx_sema = asyncio.Semaphore(max_concurrent_contexts)
        logger.debug("[%s] PlaywrightManager initialized (reuse=%s, max_ctx=%s)", self._debug_name, self.reuse_context, max_concurrent_contexts)

    def acquire_context(self):
        manager = self

        class _Ctx:
            def __init__(self):
                self._ctx = None

            async def __aenter__(self):
                logger.debug("[%s] acquiring context semaphore", manager._debug_name)
                await manager._ctx_sema.acquire()
                try:
                    if manager.reuse_context:
                        if manager._shared_ctx is None:
                            logger.debug("[%s] Creating shared BrowserContext", manager._debug_name)
                            manager._shared_ctx = await manager.browser.new_context()
                        self._ctx = manager._shared_ctx
                    else:
                        logger.debug("[%s] Creating temporary BrowserContext", manager._debug_name)
                        self._ctx = await manager.browser.new_context()
                    logger.debug("[%s] context ready", manager._debug_name)
                    return self._ctx
                except Exception:
                    logger.exception("[%s] Error creating BrowserContext", manager._debug_name)
                    manager._ctx_sema.release()
                    raise

            async def __aexit__(self, exc_type, exc, tb):
                try:
                    if not manager.reuse_context and self._ctx:
                        logger.debug("[%s] Closing temporary BrowserContext", manager._debug_name)
                        try:
                            await self._ctx.close()
                        except Exception:
                            logger.exception("[%s] Error closing temporary BrowserContext", manager._debug_name)
                    else:
                        logger.debug("[%s] Leaving shared BrowserContext open", manager._debug_name)
                finally:
                    try:
                        manager._ctx_sema.release()
                    except Exception:
                        logger.exception("[%s] Error releasing context semaphore", manager._debug_name)

        return _Ctx()

    async def close(self):
        if self._shared_ctx:
            try:
                logger.info("[%s] Closing shared context", self._debug_name)
                await self._shared_ctx.close()
            except Exception:
                logger.exception("[%s] Error closing shared context", self._debug_name)
            finally:
                self._shared_ctx = None
                logger.debug("[%s] Shared context cleared", self._debug_name)

# ----------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------
def get_cheapest(items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    try:
        logger.debug("get_cheapest called with %d items", len(items) if items else 0)
        if not items:
            return None
        valid = [it for it in items if it and ("price" in it) and (it["price"] is not None)]
        if not valid:
            logger.debug("No valid priced items found; returning first item fallback")
            return items[0] if items else None
        cheapest = min(valid, key=lambda x: x["price"])
        logger.debug("get_cheapest selected price=%s title=%s", cheapest.get("price"), cheapest.get("title"))
        return cheapest
    except Exception:
        logger.exception("get_cheapest() failed")
        return None

# NEW: The worthit_score function you provided
from typing import List, Dict, Any

def worthit_score(user_price: float, market_prices: List[float]) -> Dict[str, Any]:
    if not market_prices:
        result = {"score": None, "message": "No market prices available"}
        return result

    avg_price = sum(market_prices) / len(market_prices)
    deviation = (user_price - avg_price) / avg_price

    if user_price <= avg_price:
        # Reward for being cheaper (can exceed 100)
        score = round(100 * (1 - deviation), 2)
    else:
        # Harsher penalty for being costlier
        score = max(0, round(100 * (1 - deviation * 2), 2))

    # Messages based on score
    if score >= 110:
        message = "Unbelievable steal! Grab it right away"
    elif score >= 100:
        message = "Excellent deal! Worth every rupee"
    elif score >= 85:
        message = "Fair deal, but check alternatives"
    elif score >= 60:
        message = "Overpriced, negotiate if possible"
    else:
        message = "Not worth it, better skip"

    result = {"score": score, "avg_price": avg_price, "message": message}
    return result


# ----------------------------------------------------------------
# Embedded index page (SSE + "Load More")
# ----------------------------------------------------------------
INDEX_HTML = """
<!doctype html>
<html>
<head><meta charset="utf-8"/><title>Price Compare — Live</title>
<style>
  body{font-family:Arial,Helvetica,sans-serif;padding:16px;max-width:900px;margin:auto}
  input{width:33%;padding:8px;font-size:16px}
  button{padding:8px 12px;font-size:16px;margin-left:6px}
  .site{margin:10px 0;padding:8px;border-left:4px solid #333;background:#fff}
  pre{background:#f5f5f5;padding:12px;border-radius:6px;white-space:pre-wrap}
  .controls{margin-bottom:12px}
  #moreBtn{margin-left:10px}
  table{width:100%;border-collapse:collapse;margin-top:12px}
  th,td{padding:8px;border:1px solid #ddd}
  th{background:#222;color:#fff;text-align:left}
  .score{margin-top: 16px; padding: 12px; background-color: #eef; border: 1px solid #ccd; border-radius: 6px;}
</style>
</head>
<body>
  <h2>Price Compare — Live</h2>
  <p>Type product and your price, then click Search.</p>

  <div class="controls">
    <input id="q" placeholder="e.g. iphone 16 pro" />
    <input id="user_price" type="number" placeholder="Your Price (e.g. 75000)" />
    <button id="go">Search</button>
    <button id="moreBtn" disabled>Load More</button>
  </div>

  <div id="score_result" class="score" style="display:none;"></div>
  <div id="log"></div>

  <h3>Raw stream (debug)</h3>
  <pre id="raw"></pre>

  <h3>Table view</h3>
  <table id="table">
    <thead><tr><th>Site</th><th>Price</th><th>Rating</th><th>URL</th><th>time(s)</th></tr></thead>
    <tbody></tbody>
  </table>

<script>
const log = (msg) => {
  const d = document.createElement('div');
  d.className = 'site';
  d.innerHTML = msg;
  document.getElementById('log').prepend(d);
}
const raw = document.getElementById('raw');
const tbody = document.querySelector('#table tbody');
let currentEventSource = null;
let lastQuery = '';
let lastUserPrice = 0;
let marketPrices = [];

// --- NEW: Price formatting helper ---
function formatPrice(price) {
    if(price === undefined || price === null) return 'N/A';
    // Remove anything except digits and dot
    let cleaned = price.toString().replace(/[^\d.]/g, '');
    let numberPrice = parseFloat(cleaned);
    if(isNaN(numberPrice)) return 'N/A';
    return "₹" + numberPrice.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

document.getElementById('go').addEventListener('click', () => {
  const q = document.getElementById('q').value.trim();
  const userPrice = parseFloat(document.getElementById('user_price').value.trim());
  if(!q || !userPrice) { alert('Enter both a query and your price'); return; }
  
  lastQuery = q;
  lastUserPrice = userPrice;
  marketPrices = [];
  
  if(currentEventSource) { currentEventSource.close(); currentEventSource = null; }
  raw.textContent = '';
  tbody.innerHTML = '';
  document.getElementById('score_result').style.display = 'none';
  log('Connecting for: ' + q);

  const url = '/compare?query=' + encodeURIComponent(q) + '&user_price=' + userPrice;
  const es = new EventSource(url);
  currentEventSource = es;

  document.getElementById('moreBtn').disabled = true;

  es.onmessage = (ev) => {
    try {
      const d = JSON.parse(ev.data);
      raw.textContent += JSON.stringify(d, null, 2) + "\\n\\n";
      
      if (d.site === '_done_') {
        log('<b>All done</b> — total_time: ' + d.total_time + 's');
        if (d.worthit) {
            const scoreDiv = document.getElementById('score_result');
            scoreDiv.innerHTML = '<b>WorthIt Score: ' + d.worthit.score + '%</b><br/>' + d.worthit.message + '<br/>(Average Market Price: ' + d.worthit.avg_price.toFixed(2) + ')';
            scoreDiv.style.display = 'block';
        }
        document.getElementById('moreBtn').disabled = false;
        es.close();
        return;
      }
      
      const siteName = d.site || 'Unknown';
      const timeTaken = d.time_taken || 0;
      const result = d.result || {};

      if (result.price !== undefined && result.price !== null) {
          marketPrices.push(parseFloat(result.price.toString().replace(/[^\d.]/g, '')));
      }

      const urlCell = result.url ? '<a href="' + result.url + '" target="_blank">link</a>' : 'N/A';
      const price = formatPrice(result.price);
      const rating = result.rating || 'N/A';

      let existing = document.querySelector('tr[data-site="'+siteName.replace(/"/g,'')+'"]');
      if (!existing) {
        const tr = document.createElement('tr');
        tr.setAttribute('data-site', siteName);
        tr.innerHTML = '<td>'+siteName+'</td><td>'+price+'</td><td>'+rating+'</td><td>'+urlCell+'</td><td>'+timeTaken+'</td>';
        tbody.prepend(tr);
      } else {
        existing.innerHTML = '<td>'+siteName+'</td><td>'+price+'</td><td>'+rating+'</td><td>'+urlCell+'</td><td>'+timeTaken+'</td>';
      }

      log('<b>' + siteName + '</b> — time: ' + timeTaken + 's<br/>' + JSON.stringify(result, null, 2));
    } catch (e) {
      raw.textContent += 'parse error: ' + e + '\\n' + ev.data + '\\n';
    }
  };

  es.onerror = (err) => {
    log('<span style="color:crimson;"><b>Connection error</b></span>');
    if (currentEventSource) {
      currentEventSource.close();
      currentEventSource = null;
    }
    document.getElementById('moreBtn').disabled = false;
  };
});

document.getElementById('moreBtn').addEventListener('click', async () => {
  if (!lastQuery) return alert('Search first');
  const url = '/more?query=' + encodeURIComponent(lastQuery) + '&user_price=' + lastUserPrice;
  log('Fetching /more for: ' + lastQuery);
  try {
    const res = await fetch(url);
    if (!res.ok) {
      const err = await res.json().catch(()=>null);
      log('<span style="color:crimson;">Error fetching /more: '+ (err && err.error ? err.error : res.status) +'</span>');
      return;
    }
    const body = await res.json();
    if (body.status === 'loading') {
      log('Background still loading — try again in a moment.');
      return;
    }
    
    if (body.worthit) {
        const scoreDiv = document.getElementById('score_result');
        scoreDiv.innerHTML = '<b>WorthIt Score: ' + body.worthit.score + '%</b><br/>' + body.worthit.message + '<br/>(Average Market Price: ' + body.worthit.avg_price.toFixed(2) + ')';
        scoreDiv.style.display = 'block';
    }

    const results = body.results || body;
    for (const [site, result] of Object.entries(results)) {
      const siteName = site;
      const timeTaken = body.time_taken_background || 'N/A';
      const urlCell = result && result.url ? '<a href="'+result.url+'" target="_blank">link</a>' : 'N/A';
      const price = formatPrice(result && result.price);
      const rating = (result && result.rating) ? result.rating : 'N/A';

      if (price !== 'N/A' && !marketPrices.includes(parseFloat(result.price.toString().replace(/[^\d.]/g, '')))) {
          marketPrices.push(parseFloat(result.price.toString().replace(/[^\d.]/g, '')));
      }

      let existing = document.querySelector('tr[data-site="'+siteName.replace(/"/g,'')+'"]');
      if (!existing) {
        const tr = document.createElement('tr');
        tr.setAttribute('data-site', siteName);
        tr.innerHTML = '<td>'+siteName+'</td><td>'+price+'</td><td>'+rating+'</td><td>'+urlCell+'</td><td>'+timeTaken+'</td>';
        tbody.prepend(tr);
      } else {
        existing.innerHTML = '<td>'+siteName+'</td><td>'+price+'</td><td>'+rating+'</td><td>'+urlCell+'</td><td>'+timeTaken+'</td>';
      }
      log('<b>' + siteName + ' (more)</b> — ' + JSON.stringify(result, null, 2));
    }
  } catch (e) {
    log('<span style="color:crimson;">/more fetch failed: '+ e.message +'</span>');
  }
});
</script>

</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML

# ----------------------------------------------------------------
# Playwright init/close helpers (shared by startup and CLI test mode)
# ----------------------------------------------------------------
async def init_playwright():
    """
    Initialize Playwright, browser and PlaywrightManager.
    Assigns _manager into modules that expect it.
    Safe to call multiple times (if already initialized it will be kept).
    """
    global _playwright, _browser, _playwright_manager
    if _playwright_manager is not None:
        logger.info("init_playwright: Playwright already initialized.")
        return

    try:
        logger.info("init_playwright: attempting to start Playwright (async_playwright).")
        from playwright.async_api import async_playwright  # type: ignore

        _playwright = await async_playwright().start()

        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-software-rasterizer",
            ],
        )
        logger.info("init_playwright: Chromium launched via Playwright.")

        _playwright_manager = PlaywrightManager(_browser, reuse_context=False, max_concurrent_contexts=6, debug_name="CentralPlayMgr")
        logger.info("init_playwright: PlaywrightManager created.")

        try:
            amazon_mod._manager = _playwright_manager
            logger.info("Assigned _manager to amazon_mod")
        except Exception:
            logger.exception("Failed to assign _manager to amazon_mod")
        try:
            flipkart_mod._manager = _playwright_manager
            logger.info("Assigned _manager to flipkart_mod")
        except Exception:
            logger.exception("Failed to assign _manager to flipkart_mod")
        try:
            croma_mod._manager = _playwright_manager
            logger.info("Assigned _manager to croma_mod")
        except Exception:
            logger.exception("Failed to assign _manager to croma_mod")

        logger.info("init_playwright: Playwright manager assigned.")
    except Exception:
        logger.exception("init_playwright failed: Playwright initialization failed. Scrapers that need Playwright will fail until fixed.")
        _playwright = None
        _browser = None
        _playwright_manager = None

async def close_playwright():
    """
    Close Playwright resources if initialized.
    Safe to call even if resources are not present.
    """
    global _playwright, _browser, _playwright_manager
    logger.info("close_playwright: cleaning Playwright resources.")
    try:
        if _playwright_manager:
            try:
                await _playwright_manager.close()
            except Exception:
                logger.exception("Error closing PlaywrightManager")
            _playwright_manager = None
        if _browser:
            try:
                await _browser.close()
            except Exception:
                logger.exception("Error closing browser")
            _browser = None
        if _playwright:
            try:
                await _playwright.stop()
            except Exception:
                logger.exception("Error stopping Playwright")
        _playwright = None
        logger.info("close_playwright: Playwright resources cleaned up.")
    except Exception:
        logger.exception("close_playwright: unexpected error during Playwright cleanup")

# ----------------------------------------------------------------
# Startup/shutdown: Initialize Playwright centrally (kept for compatibility)
# ----------------------------------------------------------------
@app.on_event("shutdown")
async def shutdown_event():
    # Ensure Playwright closes gracefully
    try:
        await close_playwright()
    except Exception as e:
        print(f"[!] Playwright shutdown issue: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    await close_playwright()

# ----------------------------------------------------------------
# call_scraper_with_retries: invoke scraper with timeout and retries
# ----------------------------------------------------------------
# Background-only sites (not included in /compare immediate phase)
BACKGROUND_SITES = ["Reliance Digital", "Poorvika", "Pai International", "Sangeetha"]


async def call_scraper_with_retries(
    func: Callable[..., Any],
    query: str,
    *,
    timeout: float = 30.0,
    retries: int = 2,
    backoff: float = 1.0,
    site_name: Optional[str] = None,
) -> Any:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.info("Calling scraper %s (attempt %d/%d, timeout=%s) query=%r",
                        site_name or getattr(func, "__name__", str(func)), attempt, retries, timeout, query)

            if inspect.iscoroutinefunction(func):
                try:
                    sig = inspect.signature(func)
                    params = sig.parameters
                    expects_browser = False
                    if len(params) >= 2 or 'browser' in params:
                        expects_browser = True
                    if expects_browser and _browser is not None:
                        logger.debug("Calling async scraper %s with browser instance", func.__name__)
                        coro = func(query, _browser)
                    else:
                        logger.debug("Calling async scraper %s without browser (fallback)", func.__name__)
                        coro = func(query)
                except TypeError as te:
                    logger.warning("Signature check TypeError for %s: %s; trying fallback calling func(query)", getattr(func, "__name__", func), te)
                    coro = func(query)
                except Exception as e:
                    logger.exception("Unexpected error while preparing async call for %s: %s", getattr(func, "__name__", func), e)
                    raise

                res = await asyncio.wait_for(coro, timeout=timeout)
            else:
                if site_name in BACKGROUND_SITES:
                    logger.debug("Using selenium semaphore for site %s", site_name)
                    async with selenium_semaphore:
                        th = asyncio.create_task(asyncio.to_thread(func, query))
                        res = await asyncio.wait_for(th, timeout=timeout)
                else:
                    th = asyncio.create_task(asyncio.to_thread(func, query))
                    res = await asyncio.wait_for(th, timeout=timeout)

            logger.info("Scraper %s succeeded on attempt %d", site_name or func.__name__, attempt)
            return res

        except asyncio.TimeoutError as te:
            logger.warning("Scraper %s timed out on attempt %d/%d (timeout=%s)", site_name or func.__name__, attempt, retries, timeout)
            last_exc = te
        except Exception as e:
            logger.exception("Scraper %s raised on attempt %d/%d: %s", site_name or func.__name__, attempt, retries, e)
            last_exc = e

        if attempt < retries:
            sleep_time = backoff * attempt
            logger.info("Retrying scraper %s after %.2fs backoff", site_name or func.__name__, sleep_time)
            await asyncio.sleep(sleep_time)

    logger.error("Scraper %s failed after %d attempts", site_name or func.__name__, retries)
    raise last_exc if last_exc else RuntimeError("Scraper failed without exception")

# ----------------------------------------------------------------
# Wrapper that runs a scraper and returns tagged result
# ----------------------------------------------------------------
async def run_scraper_and_tag(func: Callable[[str], Any], query: str, timeout: float, retries: int, site_name: str) -> Dict[str, Any]:
    start = time.time()
    logger.debug("run_scraper_and_tag: starting scraper %s for query=%s", site_name, query)
    try:
        res = await call_scraper_with_retries(func, query, timeout=timeout, retries=retries, site_name=site_name)
        if res is None:
            safe_res = {"error": "no_data_returned"}
        else:
            safe_res = res
        duration = round(time.time() - start, 2)
        logger.info("run_scraper_and_tag: %s returned in %ss", site_name, duration)
        return {"site": site_name, "result": safe_res, "duration": duration}
    except Exception as e:
        duration = round(time.time() - start, 2)
        logger.exception("run_scraper_and_tag: scraper %s failed completely: %s", site_name, e)
        return {"site": site_name, "result": {"error": str(e)}, "duration": duration}

# ----------------------------------------------------------------
# schedule a scraper task
# ----------------------------------------------------------------
_task_id_map: Dict[int, str] = {}

def schedule_scraper_task(func: Callable[[str], Any], query: str, timeout: float, retries: int, site_name: str) -> asyncio.Task:
    # FIX: use the passed site_name, not 'name'
    task = asyncio.create_task(run_scraper_and_tag(func, query, timeout=timeout, retries=retries, site_name=site_name))
    _task_id_map[id(task)] = site_name
    logger.debug("Scheduled task id=%s for site=%s", id(task), site_name)

    def _on_done(t):
        try:
            _task_id_map.pop(id(t), None)
        except Exception:
            logger.exception("Error cleaning task id map for %s", id(t))

    task.add_done_callback(_on_done)
    return task

# ----------------------------------------------------------------
# Helper: gather background tasks
# ----------------------------------------------------------------
async def _gather_background_tasks(query: str, tasks: List[asyncio.Task]) -> Dict[str, Any]:
    logger.info("_gather_background_tasks: started for query=%s with %d tasks", query, len(tasks))
    try:
        done = await asyncio.gather(*tasks, return_exceptions=True)
        out: Dict[str, Any] = {}
        for idx, item in enumerate(done):
            try:
                if isinstance(item, Exception):
                    tid = id(tasks[idx])
                    site_name = _task_id_map.get(tid, f"task_{idx}")
                    logger.warning("_gather_background_tasks: task %s completed with exception: %s", site_name, item)
                    out[site_name] = {"error": str(item)}
                else:
                    site = item.get("site", _task_id_map.get(id(tasks[idx]), f"task_{idx}"))
                    res = item.get("result", {})
                    out[site] = res
            except Exception:
                logger.exception("Error processing background result item index=%d", idx)
                out[f"item_{idx}"] = {"error": "processing_failed"}
        logger.info("_gather_background_tasks: finished for query=%s", query)
        return out
    except Exception:
        logger.exception("_gather_background_tasks: fatal error for query=%s", query)
        raise

# ----------------------------------------------------------------
# /compare SSE endpoint
# ----------------------------------------------------------------
@app.get("/compare")
async def compare_products(request: Request, query: str = Query(..., min_length=1), user_price: float = Query(...)):
    total_start = time.time()
    q = query.strip()
    lower_q = q.lower()
    logger.info("Compare request: %s, User Price: %f", q, user_price)

    immediate_ordered: List[Tuple[Callable[[str], Any], str]] = [
        (get_cheapest_croma_product, "Croma"),
        (fetch_flipkart_products, "Flipkart"),
        (scrape_amazon, "Amazon"),
    ]
    background_ordered: List[Tuple[Callable[[str], Any], str]] = [
        (scrape_reliance_product, "Reliance Digital"),
        (get_cheapest_poorvika_product, "Poorvika"),
        (get_cheapest_pai_product, "Pai International"),
        (scrape_sangeetha_product, "Sangeetha"),
    ]

    per_site_timeout = {"Croma": 25.0, "Flipkart": 30.0, "Amazon": 30.0,
                        "Reliance Digital": 60.0, "Poorvika": 60.0, "Pai International": 60.0, "Sangeetha": 60.0}
    per_site_retries = {"Croma": 2, "Flipkart": 2, "Amazon": 2,
                        "Reliance Digital": 2, "Poorvika": 2, "Pai International": 2, "Sangeetha": 2}

    immediate_tasks: List[asyncio.Task] = []
    for func, name in immediate_ordered:
        timeout = per_site_timeout.get(name, 30.0)
        retries = per_site_retries.get(name, 2)
        t = schedule_scraper_task(func, q, timeout=timeout, retries=retries, site_name=name)
        immediate_tasks.append(t)

    background_tasks: List[asyncio.Task] = []
    for func, name in background_ordered:
        timeout = per_site_timeout.get(name, 60.0)
        retries = per_site_retries.get(name, 2)
        t = schedule_scraper_task(func, q, timeout=timeout, retries=retries, site_name=name)
        background_tasks.append(t)

    if lower_q in background_results and not background_results[lower_q].done():
        logger.info("Background tasks already exist and are running for query=%s", lower_q)
    else:
        gather_task = asyncio.create_task(_gather_background_tasks(q, background_tasks))
        background_results[lower_q] = gather_task
        # FIX logging placeholder mismatch
        logger.info("Background gather task scheduled for query=%s (task_id=%s)", lower_q, id(gather_task))

    async def event_stream():
        market_prices = []
        try:
            logger.info("Starting SSE streaming for immediate tasks for query=%s", q)
            for done_future in asyncio.as_completed(immediate_tasks):
                tagged = await done_future
                site = tagged.get("site", "Unknown")
                res = tagged.get("result", {})
                
                if res and res.get("price") is not None:
                    market_prices.append(res["price"])

                elapsed = round(time.time() - total_start, 2)
                payload = {"site": site, "result": res, "time_taken": elapsed}
                yield "data: " + json.dumps(payload, default=str) + "\n\n"

                if await request.is_disconnected():
                    logger.info("Client disconnected; cancelling remaining immediate scrapers.")
                    for t in immediate_tasks:
                        if not t.done(): t.cancel()
                    return

            total = round(time.time() - total_start, 2)
            logger.info("Immediate streaming complete for query=%s in %ss.", q, total)
            
            # Calculate WorthIt score with immediate results
            score_data = worthit_score(user_price, market_prices)
            
            yield "data: " + json.dumps({"site": "_done_", "total_time": total, "worthit": score_data}) + "\n\n"

        except Exception:
            logger.exception("Error in SSE generator for query=%s", q)
            raise

    return StreamingResponse(event_stream(), media_type="text/event-stream")

# ----------------------------------------------------------------
# Background fetch when explicitly requested (/more)
# ----------------------------------------------------------------
# ADDED: define the helper used when no running background task exists
async def fetch_more_products_on_demand(query: str) -> Dict[str, Any]:
    q = query.strip()
    background_ordered: List[Tuple[Callable[[str], Any], str]] = [
        (scrape_reliance_product, "Reliance Digital"),
        (get_cheapest_poorvika_product, "Poorvika"),
        (get_cheapest_pai_product, "Pai International"),
        (scrape_sangeetha_product, "Sangeetha"),
    ]
    per_site_timeout = {"Reliance Digital": 60.0, "Poorvika": 60.0, "Pai International": 60.0, "Sangeetha": 60.0}
    per_site_retries = {"Reliance Digital": 2, "Poorvika": 2, "Pai International": 2, "Sangeetha": 2}

    tasks: List[asyncio.Task] = []
    for func, name in background_ordered:
        t = schedule_scraper_task(func, q, timeout=per_site_timeout[name], retries=per_site_retries[name], site_name=name)
        tasks.append(t)
    return await _gather_background_tasks(q, tasks)

@app.get("/more")
async def get_more_products(query: str = Query(..., min_length=1), user_price: Optional[float] = Query(None)):
    lower_q = query.strip().lower()
    task = background_results.get(lower_q)

    # Default empty worthit if user_price is missing
    def empty_worthit():
        return {"score": None, "avg_price": None, "message": "No data yet"}

    if not task:
        try:
            result = await fetch_more_products_on_demand(query)
            market_prices = [p['price'] for p in result.values() if p and p.get('price') is not None]
            score_data = worthit_score(user_price, market_prices) if user_price else empty_worthit()
            return {"query": query, "results": result, "worthit": score_data}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)

    if task.done():
        try:
            res = task.result()
            market_prices = [p['price'] for p in res.values() if p and p.get('price') is not None]
            score_data = worthit_score(user_price, market_prices) if user_price else empty_worthit()
            return {"query": query, "results": res, "worthit": score_data}
        except Exception as e:
            return JSONResponse({"error": str(e)}, status_code=500)
    else:
        # Background still running, return placeholder worthit
        return {"query": query, "status": "loading", "worthit": empty_worthit()}

# ----------------------------------------------------------------
# CLI test mode (keeps same behavior)
# ----------------------------------------------------------------
async def _run_parallel_and_print(query: str):
    total_start = time.time()
    logger.info("CLI test run for: %s", query)
    ordered = [
        (get_cheapest_croma_product, "Croma"),
        (fetch_flipkart_products, "Flipkart"),
        (scrape_amazon, "Amazon"),
    ]
    # FIXED: correct schedule_scraper_task signature
    tasks = [
        schedule_scraper_task(func, query, timeout=15, retries=1, site_name=tag)
        for tag, func in [
            ("Reliance Digital", scrape_reliance_product),
            ("Poorvika", get_cheapest_poorvika_product),
            ("Pai International", get_cheapest_pai_product),
            ("Sangeetha", scrape_sangeetha_product),
        ] if tag in BACKGROUND_SITES
    ]

    for done in asyncio.as_completed(tasks):
        try:
            tagged = await done
        except Exception as e:
            logger.error("CLI task failed: %s", e)
            tagged = {"site": _task_id_map.get(id(done), "Unknown"), "result": {"error": str(e)}}
        site = tagged.get("site", _task_id_map.get(id(done), "Unknown"))
        res = tagged.get("result", {})
        
        normalized = res
        
        elapsed = round(time.time() - total_start, 2)
        print(f"\n--- {site} (at {elapsed}s) ---")
        print(json.dumps(normalized, indent=2, default=str))

    total = round(time.time() - total_start, 2)
    print("\n*** All done (total_time: %.2fs) ***" % total)

async def async_main_test(query: str):
    await init_playwright()
    try:
        await _run_parallel_and_print(query)
    finally:
        await close_playwright()

def run_cli_test(query: str):
    asyncio.run(async_main_test(query))
# ----------------------------------------------------------------
# Warmup first 3 scrapers on startup (simulate first query for faster later responses)
# ----------------------------------------------------------------Query
@app.on_event("startup")
async def warmup_first_scrapers():
    await init_playwright()
    logger.info("Warming up first 3 scrapers with sample query 'iphone 16'")
    sample_query = "iphone 16"
    try:
        first_three = [
            (get_cheapest_croma_product, "Croma"),
            (fetch_flipkart_products, "Flipkart"),
            (scrape_amazon, "Amazon"),
        ]
        tasks = []
        for func, name in first_three:
            t = schedule_scraper_task(func, sample_query, timeout=30.0, retries=1, site_name=name)
            tasks.append(t)
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("Warmup complete for first 3 scrapers.")
    except Exception:
        logger.exception("Warmup failed.")

# ----------------------------------------------------------------
# Entrypoint
# ----------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run price-compare server or test mode.")
    parser.add_argument("--test", "-t", type=str, help="Run test mode for a single query (prints to terminal).")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host for server")
    parser.add_argument("--port", type=int, default=8000, help="Port for server")
    args = parser.parse_args()

    if args.test:
        run_cli_test(args.test)
    else:
        logger.info("Starting server on http://%s:%s (open / in browser)", args.host, args.port)
        uvicorn.run(app, host=args.host, port=args.port, log_level="info", reload=False)
