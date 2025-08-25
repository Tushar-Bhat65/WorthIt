# croma.py
import os
import time
import re
import logging
import urllib.parse
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, ElementNotInteractableException
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

# --- LOGGING ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- UNCHANGED HELPER FUNCTIONS (kept exact names & behavior) ---
def is_strict_match(query: str, title: str) -> bool:
    normalized_query = re.sub(r'\s+', '', query.lower())
    normalized_title = re.sub(r'\s+', '', title.lower())

    disallowed_patterns = re.compile(f"{re.escape(normalized_query)}(pro|plus|max|ultra|pro max)")
    if disallowed_patterns.search(normalized_title):
        return False
    return normalized_query in normalized_title

# --- Persistent Selenium Manager ---
class PersistentSeleniumManager:
    def __init__(self):
        self.driver: Optional[webdriver.Chrome] = None
        self.started = False

    def start(self, headless: bool = True, window_size: str = "1366,768"):
        if self.started:
            return

        options = webdriver.ChromeOptions()
        if headless:
            try:
                options.add_argument("--headless=new")
            except Exception:
                options.add_argument("--headless")
                options.add_argument("--disable-gpu")
        options.add_argument(f"--window-size={window_size}")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

        try:
            options.page_load_strategy = "eager"
        except Exception:
            pass

        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)

        chromedriver_path = os.environ.get("CHROMEDRIVER_PATH")
        if chromedriver_path:
            service = Service(chromedriver_path)
        else:
            service = Service(ChromeDriverManager().install())

        try:
            self.driver = webdriver.Chrome(service=service, options=options)
            try:
                self.driver.set_page_load_timeout(6)
            except Exception:
                pass
            self.started = True
            logger.info(f"[PersistentSeleniumManager] Started Chrome driver (headless={headless})")
        except WebDriverException as e:
            logger.error(f"[PersistentSeleniumManager] WebDriver start error: {e}")
            self.driver = None
            self.started = False
            raise

    def stop(self):
        try:
            if self.driver:
                self.driver.quit()
                logger.info("[PersistentSeleniumManager] Browser closed")
        except Exception:
            pass
        finally:
            self.driver = None
            self.started = False

# Global singleton
_selenium_manager: PersistentSeleniumManager | None = None

def _get_manager() -> PersistentSeleniumManager:
    global _selenium_manager
    if _selenium_manager is None:
        _selenium_manager = PersistentSeleniumManager()
        _selenium_manager.start(headless=True)
    elif not _selenium_manager.started:
        _selenium_manager.start(headless=True)
    return _selenium_manager

# --- FETCH FUNCTION ---
def fetch_croma_html(query: str) -> str | None:
    logger.info(f"[Croma Scraper] Searching for: '{query}'")
    html = None

    manager = _get_manager()
    driver = manager.driver
    if driver is None:
        logger.error("[✘] No webdriver available.")
        return None

    try:
        wait = WebDriverWait(driver, 4, poll_frequency=0.25)
        start_time = time.time()
        encoded_query = urllib.parse.quote_plus(query)
        search_url = f"https://www.croma.com/searchB?q={encoded_query}%3Arelevance"

        try:
            driver.get("https://www.croma.com/")
            logger.debug("[✓] Navigated to Croma homepage to type query")

            try:
                search_input = wait.until(EC.presence_of_element_located((By.ID, "searchV2")))
                time.sleep(0.25)
                try:
                    search_input.click()
                except Exception:
                    pass
                try:
                    search_input.clear()
                except Exception:
                    pass
                search_input.send_keys(query)
                search_input.send_keys(Keys.ENTER)
                logger.info("[✓] Typed query into search input and submitted")
            except TimeoutException:
                logger.warning("[!] searchV2 input not found. Falling back to direct URL.")
                raise

            try:
                product_selector = "li.product-item, .product-card, .product-grid-item, div.product-item, div.search-result-item"
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, product_selector)))
                logger.info("[✓] Product container detected after typing")
            except TimeoutException:
                logger.warning("[!] Timeout waiting for product-item after typing")

        except Exception:
            try:
                driver.get(search_url)
                logger.debug("[✓] Navigated directly to Croma search URL (fallback)")
                product_selector = "li.product-item, .product-card, .product-grid-item, div.product-item, div.search-result-item"
                try:
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, product_selector)))
                    logger.info("[✓] Product container detected in DOM (fallback)")
                except TimeoutException:
                    logger.warning("[!] Timeout waiting for product-item on direct URL")
            except Exception as e:
                logger.error(f"[✘] Error navigating to search URL fallback: {e}")

        html = driver.page_source
        end_time = time.time()
        logger.info(f"[⏱] Fetch Time: {end_time - start_time:.2f} seconds")

    except WebDriverException as e:
        logger.error(f"[✘] WebDriver error fetching Croma HTML: {e}")
    except Exception as e:
        logger.error(f"[✘] Error fetching Croma HTML: {e}")

    return html

# --- PARSING ---
def parse_croma_html(html: str, query: str) -> List[Dict[str, Any]]:
    start_time = time.time()
    parser_name = "html.parser"
    try:
        BeautifulSoup("<x/>", "lxml")
        parser_name = "lxml"
    except Exception:
        pass

    soup = BeautifulSoup(html, parser_name)

    card_selectors = [
        "li.product-item",
        ".product-card",
        ".product-grid-item",
        "div.product-item",
        "div.search-result-item",
        ".search-list-item"
    ]

    cards = []
    for sel in card_selectors:
        cards.extend(soup.select(sel))

    seen, unique_cards = set(), []
    for c in cards:
        identifier = str(c)[:200]
        if identifier not in seen:
            seen.add(identifier)
            unique_cards.append(c)
    cards = unique_cards

    if not cards:
        logger.warning("[✘] No product containers found.")
        return []

    results: List[Dict[str, Any]] = []
    for card in cards:
        try:
            title_tag = None
            for tsel in ["h3.product-title a", "a.product-name", "h2.product-title a", "a.item-title", "a[href] .product-name", "a[title]"]:
                title_tag = card.select_one(tsel)
                if title_tag:
                    break
            if not title_tag:
                title_tag = card.find("a")

            price_tag = None
            for psel in ["span[data-testid='new-price']", "span.price", "span.final-price", "div.price", "span[itemprop='price']", ".product-price"]:
                price_tag = card.select_one(psel)
                if price_tag:
                    break

            rating_tag = None
            for rsel in ["span.rating-text", ".rating", ".stars", "div.rating", "span[itemprop='ratingValue']"]:
                rating_tag = card.select_one(rsel)
                if rating_tag:
                    break

            if not (title_tag and price_tag):
                continue

            title = title_tag.get_text(strip=True)
            if not is_strict_match(query, title):
                continue

            url = title_tag.get("href", "")
            full_url = f"https://www.croma.com{url}" if url.startswith("/") else url
            price = extract_price(price_tag.get_text())
            rating = rating_tag.get_text(strip=True) if rating_tag else "Not Available"

            if price is not None:
                results.append({
                    "title": title,
                    "price": price,
                    "rating": rating,
                    "url": full_url
                })
        except Exception:
            continue

    end_time = time.time()
    logger.info(f"[⏱] Parsing Time: {end_time - start_time:.2f} seconds")
    return sorted(results, key=lambda x: x["price"])

# --- PRICE HELPER ---
def extract_price(text: str) -> Optional[float]:
    try:
        cleaned = re.sub(r"[^\d.]", "", text.replace(",", ""))
        if not cleaned:
            return None
        return float(cleaned)
    except Exception:
        return None

# --- MAIN ---
def get_cheapest_croma_product(query: str):
    html = fetch_croma_html(query)
    if not html:
        logger.error("[✘] Could not retrieve HTML.")
        return

    results = parse_croma_html(html, query)
    if not results:
        print("No matching products found.")
        return

    best = results[0]
    print("\n--- Cheapest Exact Match on Croma ---")
    print(f"₹{best['price']}")
    print(f"{best['title']}")
    print(f"Rating: {best['rating']}")
    print(f"URL: {best['url']}")
    return best

# --- DRIVER CONTROL ---
def start_persistent_driver(headless: bool = True):
    mgr = _get_manager()
    if not mgr.started:
        mgr.start(headless=headless)
    return mgr

def stop_persistent_driver():
    global _selenium_manager
    if _selenium_manager:
        _selenium_manager.stop()
        _selenium_manager = None

# --- EXECUTION ---
if __name__ == "__main__" or "__file__" not in globals():
    product_name = input("Enter product name (e.g. 'iPhone 16'): ").strip()
    if product_name:
        start_persistent_driver(headless=True)
        try:
            get_cheapest_croma_product(product_name)
        finally:
            stop_persistent_driver()
