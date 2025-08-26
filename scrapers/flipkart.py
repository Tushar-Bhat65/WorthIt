import asyncio
#import nest_asyncio
import re
import time
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Route, Request

#nest_asyncio.apply()

# --- CONFIG ---
HARD_ACCESSORY_KEYWORDS = {
    'case', 'cover', 'charger', 'cable', 'glass', 'tempered', 'protector',
    'adapter', 'earbuds', 'headphones', 'earphones', 'screen', 'screenprotector',
    'backcover', 'back', 'back-cover', 'skin', 'spare', 'replacement', 'parts'
}
VARIANT_KEYWORDS = {"pro", "max", "lite", "plus", "e", "se", "ultra", "mini", "fe", "promax"}
COMMON_STOPWORDS = {
    'mobile', 'phone', 'with', 'and', 'works', 'for', 'the', 'in', 'a', 'an',
    'new', 'smartphone', 'dual', 'sim', 'edition', 'version', 'model', 'capacity',
    'cellular', 'unlocked', 'brand', 'only', 'available'
}
COLOR_KEYWORDS = {
    'black', 'white', 'red', 'blue', 'green', 'yellow', 'gold', 'silver',
    'titanium', 'natural', 'desert', 'pink', 'purple', 'graphite', 'space', 'grey', 'gray', 'teal', 'ultramarine'
}
STORAGE_RE = re.compile(r'\b\d+(\.\d+)?\s*(gb|tb|mb)\b', flags=re.I)

# --- HELPERS ---
def clean_price(text: str) -> Optional[int]:
    if not text:
        return None
    groups = re.findall(r'\d[\d,\.]*', text)
    if not groups:
        return None
    best = max(groups, key=lambda s: len(re.sub(r'[^0-9]', '', s)))
    num = re.sub(r'[^\d]', '', best)
    return int(num) if num else None

def normalize(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokenize(s: str) -> List[str]:
    return [w for w in s.split() if w]

def is_relevant(query: str, title: str, price: Optional[int]) -> (bool, str):
    if not title or not query:
        return (False, "Title or query is empty")
    q_norm = normalize(query)
    t_norm = normalize(title)
    t_norm = STORAGE_RE.sub(" ", t_norm)
    query_words = tokenize(q_norm)
    title_words = tokenize(t_norm)
    if price and price < 5000:
        return (False, f"Price too low: ₹{price}")
    hw_in_title = [k for k in HARD_ACCESSORY_KEYWORDS if k in title_words]
    if hw_in_title and not all(q in title_words for q in query_words):
        return (False, f"Accessory keyword(s): {', '.join(hw_in_title)}")
    filtered = [w for w in title_words if w not in COMMON_STOPWORDS and w not in COLOR_KEYWORDS and not (w.isdigit() and len(w) >= 4)]
    if any(q not in filtered for q in query_words):
        return (False, "Missing query word")
    query_variants = set(q for q in query_words if q in VARIANT_KEYWORDS)
    title_variants = set(w for w in filtered if w in VARIANT_KEYWORDS)
    if query_variants:
        if title_variants - query_variants:
            return (False, "Extra variant found")
    return (True, "Match")

# --- Persistent Browser Manager ---
class FlipkartScraper:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None

    async def start(self, headless: bool = True):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless, args=["--no-sandbox"])
        self.context = await self.browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"),
            locale="en-IN"
        )
        await self.context.route("**/*", self._block_resources)

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _block_resources(self, route: Route, request: Request):
        if request.resource_type in ("image", "stylesheet", "font", "media"):
            await route.abort()
        else:
            await route.continue_()

    async def scrape_flipkart(self, query: str, max_items: int = 6, timeout: int = 15000) -> Dict[str, Any]:
        page = await self.context.new_page()
        start_time = time.time()
        try:
            await page.goto(f"https://www.flipkart.com/search?q={query.replace(' ', '+')}",
                            wait_until="domcontentloaded", timeout=timeout)
            await page.wait_for_selector("div[data-id], div._13oc-S, div._1xHGtK, div.slAVV4, div._4ddWXP, div.cPHb8h",
                                         state="attached", timeout=5000)

            raw_products = await page.evaluate(f"""
            () => {{
                return Array.from(document.querySelectorAll("div[data-id], div._13oc-S, div._1xHGtK, div.slAVV4, div._4ddWXP, div.cPHb8h"))
                    .slice(0, {max_items}).map(item => {{
                        const title = item.querySelector("a.s1Q9rs, div._4rR01T, span.B_NuCI, a.WKTcLC, a.IRpwTa, a.wjcEIp, span.wjcEIp, ._2WkVRV, .KzDlHZ, ._3Djpdu, a._2UzuFa, ._2B_pCR, div._2cLu-l")?.innerText?.trim() || null;
                        const priceText = item.querySelector("div._30jeq3, div._1_WHN1, div.Nx9bqj, ._25b18c, div._3_M9q6, div._1-HjSm, div.yT_W-Q")?.innerText || null;
                        const ratingText = item.querySelector("div._3LWZlK, div.XQDdHH, span.Y1HWO0, div.gUuXy-")?.innerText || null;
                        const link = item.querySelector("a._2UzuFa, a.s1Q9rs, a.WKTcLC, a.rPDeLR, a._1fQZEK, a.VJA3rP, a.wjcEIp, a.DMMoT0, a.CGtC98, a.IRpwTa, a._2kHMtA, a.zabNxf, a.t-pElj")?.href || null;
                        return {{ title, priceText, ratingText, url: link }};
                    }});
            }}
            """)

            relevant = []
            for p in raw_products:
                price_val = clean_price(p["priceText"])
                ok, _ = is_relevant(query, p["title"] or "", price_val)
                if ok:
                    relevant.append({
                        "title": p["title"],
                        "price": price_val,
                        "rating": p["ratingText"].split()[0] if p["ratingText"] else None,
                        "url": p["url"] if p["url"] else f"https://www.flipkart.com/search?q={query.replace(' ', '+')}"
                    })

            if relevant:
                cheapest = min(relevant, key=lambda x: x["price"])
                cheapest["time_taken"] = round(time.time() - start_time, 2)
                return cheapest
            return {}

        finally:
            await page.close()

# --- Exported Function ---
_scraper_instance: FlipkartScraper = None

async def fetch_flipkart_products(query: str) -> Dict[str, Any]:
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = FlipkartScraper()
        await _scraper_instance.start(headless=True)
    return await _scraper_instance.scrape_flipkart(query)

# Backward compatibility alias
scrape_flipkart = fetch_flipkart_products

# --- Demo ---
if __name__ == "__main__":
    async def main():
        query = input("Enter product name: ").strip()
        start_time = time.time()
        result = await fetch_flipkart_products(query)
        print(result or "No relevant products found.")
        print(f"⏱ Time: {time.time() - start_time:.2f}s")
    asyncio.run(main())
