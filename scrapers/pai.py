# optimized_pai_fast.py
import time
import re
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_price(price_text):
    if not price_text:
        return None
    numbers = re.findall(r'[\d,]+\.?\d*', price_text)
    if numbers:
        return float(numbers[0].replace(",", ""))
    return None


def normalize_text(text: str) -> str:
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def is_strict_match(query: str, title: str) -> bool:
    query_words = set(normalize_text(query).split())
    title_words = set(normalize_text(title).split())
    disallowed = {"pro", "plus", "max", "ultra", "promax", "pro max", "mini"}
    extra = title_words - query_words
    if any(var in extra for var in disallowed):
        return False
    return query_words.issubset(title_words)


def fetch_pai_html(query: str) -> str | None:
    """
    Optimized fetch: robustly finds/sets the search input and submits via JS fallback
    if the element isn't clickable. Returns HTML string or None on failure.
    """
    start_total = time.perf_counter()
    html = None
    driver = None
    try:
        options = webdriver.ChromeOptions()
        # headless mode (new where available)
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1366,768")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/115.0 Safari/537.36")

        # Block images/styles/fonts to reduce load
        prefs = {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2
        }
        options.add_experimental_option("prefs", prefs)

        # Eager gives DOMContentLoaded (safer than 'none' for interactive elements)
        options.page_load_strategy = "eager"

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)

        # Optional: use CDP to block common heavy resources (best-effort)
        try:
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setBlockedURLs", {"urls": ["*.png", "*.jpg", "*.gif", "*.css", "*.woff2", "*.woff", "*.svg"]})
        except Exception:
            # Not fatal — keep going without CDP blocking
            pass

        wait = WebDriverWait(driver, 4)  # small wait; we prefer fast fallbacks

        t0 = time.perf_counter()
        driver.get("https://www.paiinternational.in/")
        # Try a short wait for the input to be present/clickable
        search_input = None
        try:
            search_input = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.search-header-input")))
            # try to make it clickable if possible (fast)
            try:
                wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.search-header-input")))
            except TimeoutException:
                # it's present but maybe not "clickable" yet; we'll still attempt to interact
                pass
        except TimeoutException:
            # presence didn't appear fast enough — we'll use JS fallback below
            pass

        # If we found element normally, try sending keys
        if search_input is not None:
            try:
                search_input.clear()
                search_input.send_keys(query)
                search_input.send_keys(Keys.RETURN)
            except WebDriverException:
                # fallback to JS submission if direct send_keys fails
                search_input = None

        # JS fallback: set value and submit using form/button if element wasn't usable
        if search_input is None:
            js_submit = """
            const q = arguments[0];
            const sel = 'input.search-header-input';
            const el = document.querySelector(sel);
            if (!el) return false;
            el.focus();
            el.value = q;
            el.dispatchEvent(new Event('input', {bubbles:true}));
            // Try to submit via nearest form
            const f = el.closest('form');
            if (f) { try { f.submit(); return true; } catch(e){} }
            // Fallback: find a search button and click
            const btn = document.querySelector('button[type=submit], button.search-btn, button.icon-search, button.search-button');
            if (btn) { try { btn.click(); return true; } catch(e){} }
            // If nothing else, dispatch Enter key events
            el.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', keyCode:13, which:13, bubbles:true}));
            el.dispatchEvent(new KeyboardEvent('keyup', {key:'Enter', keyCode:13, which:13, bubbles:true}));
            return true;
            """
            try:
                ok = driver.execute_script(js_submit, query)
                if not ok:
                    # nothing to submit - try clicking a common search icon
                    try:
                        maybe_btn = driver.find_element(By.CSS_SELECTOR, "button.icon-search, button.search-button, button[type=submit]")
                        maybe_btn.click()
                    except Exception:
                        pass
            except Exception:
                # JS injection failed — continue and attempt to proceed to results polling
                pass

        # After submit, wait for product containers; if not found quickly, poll for a short time
        found = False
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-box_details")))
            found = True
        except TimeoutException:
            # Poll manually for up to ~4 seconds
            poll_until = time.time() + 4.0
            while time.time() < poll_until:
                elems = driver.find_elements(By.CSS_SELECTOR, "div.product-box_details")
                if elems:
                    found = True
                    break
                time.sleep(0.25)

        if not found:
            # No results container detected — capture page anyway (maybe site returned different structure)
            logger.warning("[Pai] Results container not detected after submit; capturing page anyway.")
        html = driver.page_source
        t1 = time.perf_counter()
        logger.info("[Pai] page fetch took %.2fs", t1 - t0)

    except Exception as e:
        logger.exception("[✘] Error fetching Pai results: %s", e)
        html = None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass
        total = time.perf_counter() - start_total
        logger.info("[Pai] total fetch cycle: %.2fs", total)
    return html


# parse_pai_html and get_cheapest_pai_product remain the same as your parser;
# Paste them from your existing code (no changes) so the data retrieval is unchanged.
# For convenience below I'll include the unchanged parse and get_cheapest functions:

def parse_pai_html(html: str, query: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.product-box_details")
    if not cards:
        print("[✘] No product containers found.")
        return []

    results = []
    for card in cards:
        title_tag = card.select_one("a.product_name")
        price_tag = card.select_one("div.price_new")

        if not (title_tag and price_tag):
            continue

        title = title_tag.get_text(strip=True)
        if not is_strict_match(query, title):
            continue

        price = extract_price(price_tag.get_text(strip=True))
        url = "https://www.paiinternational.in" + title_tag["href"] if title_tag.has_attr("href") else "Not Available"

        if price:
            results.append({
                "title": title,
                "price": price,
                "rating": "Not Available",
                "url": url
            })

    results.sort(key=lambda x: x["price"])
    return results


def get_cheapest_pai_product(query: str):
    html = fetch_pai_html(query)
    if not html:
        print("[✘] Could not retrieve HTML.")
        return

    results = parse_pai_html(html, query)
    if not results:
        print("No matching products found.")
        return

    best = results[0]
    print("\n--- Cheapest Exact Match on Pai International ---")
    print(f"₹{best['price']}")
    print(f"{best['title']}")
    print(f"Rating: {best['rating']}")
    print(f"URL: {best['url']}")
    return best


# For Jupyter/script usage:
if __name__ == "__main__" or "__file__" not in globals():
    q = input("Enter product name (e.g. 'iPhone 16'): ").strip()
    if q:
        get_cheapest_pai_product(q)
