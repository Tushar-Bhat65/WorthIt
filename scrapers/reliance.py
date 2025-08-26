import time
import re
import logging
from typing import Optional, List, Tuple
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONSTANTS ---
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
    'titanium', 'natural', 'desert', 'pink', 'purple', 'graphite', 'space',
    'grey', 'gray', 'teal', 'ultramarine'
}
STORAGE_RE = re.compile(r'\b\d+(\.\d+)?\s*(gb|tb|mb)\b', flags=re.I)

# --- HELPERS ---
def clean_price(text: str) -> Optional[int]:
    """
    Cleans and converts a price string to an integer,
    handling prices in both rupees and paise.
    """
    if not text:
        return None
    
    # Remove all non-digit and non-decimal characters, keeping only numbers and dots
    cleaned_text = re.sub(r'[^\d.]', '', text)
    
    try:
        price = float(cleaned_text)
        
        # Heuristic: if price is huge (e.g., 5674900), assume paise and divide by 100
        if price > 100000 and '.' not in text:
            price = price / 100
        
        # Round to 2 decimals if needed
        price = round(price, 2)
        
        return int(price)
        
    except (ValueError, IndexError):
        return None


def normalize(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def tokenize(s: str) -> List[str]:
    return [w for w in s.split() if w]

def is_relevant(query: str, title: str, price: Optional[int]) -> Tuple[bool, str]:
    """
    Checks if a product is relevant to the search query, with improved
    filtering for accessories.
    """
    if not title or not query:
        return (False, "Title or query is empty")

    q_norm = normalize(query)
    t_norm = normalize(title)

    query_words = tokenize(q_norm)
    title_words = tokenize(t_norm)

    # Accessory filter: Check if the query itself is for an accessory
    query_has_accessory = any(k in query_words for k in HARD_ACCESSORY_KEYWORDS)

    # If the product title contains an accessory keyword, and the query is not
    # for an accessory, it's irrelevant.
    if any(k in title_words for k in HARD_ACCESSORY_KEYWORDS) and not query_has_accessory:
        return (False, "Product is an accessory, but query is not.")

    # Price sanity check
    if price is not None and price < 5000:
        return (False, f"Price too low: ₹{price}")

    # Remove stopwords, colors, and year-like digits from title for a cleaner comparison
    filtered = [
        w for w in title_words
        if w not in COMMON_STOPWORDS
        and w not in COLOR_KEYWORDS
        and not (w.isdigit() and len(w) >= 4)
    ]

    # All key query words (excluding stopwords/variants) must be in the filtered title words
    query_key_words = [w for w in query_words if w not in COMMON_STOPWORDS]
    if any(q not in filtered for q in query_key_words):
        return (False, "Missing a key query word in title")

    # Variant consistency check
    query_variants = set(q for q in query_words if q in VARIANT_KEYWORDS)
    title_variants = set(w for w in filtered if w in VARIANT_KEYWORDS)
    if query_variants and title_variants != query_variants:
        return (False, "Variant mismatch")

    return (True, "Match")

def extract_rating_from_card(card) -> str:
    try:
        rating_block = card.select_one("div.product-card-rating")
        if not rating_block:
            return "Not Available"
        stars = rating_block.select("ul.rating-star li svg path")
        if not stars:
            return "Not Available"
        filled = sum(1 for s in stars if s.get("fill") and s["fill"].lower() == "#f7ab20")
        total = 5
        rating = f"{filled} / {total}"
        review_span = rating_block.select_one("span.detail")
        if review_span:
            reviews = review_span.get_text(strip=True)
            return f"{rating} ({reviews} reviews)"
        return rating
    except Exception as e:
        logger.warning(f"[!] Failed to extract rating: {e}")
        return "Not Available"

# --- MAIN SCRAPER ---
def scrape_reliance_product(query: str):
    logger.info(f"[Reliance Scraper] Searching for: '{query}'")
    page_source = None
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10)

        driver.get("https://www.reliancedigital.in/")
        logger.info("[✓] Homepage loaded")

        try:
            wait.until(EC.element_to_be_clickable((By.ID, "wzrk-cancel"))).click()
            logger.info("[✓] Popup dismissed")
        except Exception:
            logger.info("[i] No popup to dismiss.")

        search_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search Products & Brands']")))
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.ENTER)

        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.product-card-details")))
        page_source = driver.page_source
        logger.info("[✓] Page loaded and captured")

    except Exception as e:
        logger.error(f"[✘] Error during page load: {e}")
    finally:
        if driver:
            driver.quit()
            logger.info("[✓] Browser closed")

    if not page_source:
        logger.error("[✘] Failed to capture page HTML.")
        return None

    soup = BeautifulSoup(page_source, "html.parser")
    cards = soup.select("div.product-card-details")
    if not cards:
        logger.warning("[✘] No product cards found.")
        return None

    logger.info(f"[i] Found {len(cards)} product(s). Filtering...")

    results = []
    for card in cards:
        title_tag = card.select_one("div.product-card-title")
        url_tag = card.select_one("a.details-container")
        price_tag = card.select_one("div.price")

        if not (title_tag and url_tag and price_tag):
            continue

        title = title_tag.get_text(strip=True)
        url = "https://www.reliancedigital.in" + url_tag["href"]
        price = clean_price(price_tag.get_text())
        rating = extract_rating_from_card(card)

        ok, reason = is_relevant(query, title, price)
        if not ok:
            logger.info(f"[✘] Skipped: {title} ({reason})")
            continue

        if price:
            results.append({
                "title": title,
                "price": price,
                "rating": rating,
                "url": url
            })

    if not results:
        logger.warning(f"[✘] No relevant products found for '{query}'")
        return None

    results.sort(key=lambda x: x["price"])
    return results[0]

if __name__ == '__main__':
    product = input("Enter product name (e.g. 'Vivo X200 5G'): ").strip()
    if product:
        data = scrape_reliance_product(product)
        if data:
            print("\n--- Scraped Product Data ---")
            print(f"  Title : {data['title']}")
            print(f"  Price : ₹{data['price']}")
            print(f"  Rating: {data['rating']}")
            print(f"  URL   : {data['url']}")
            pd.DataFrame([data]).to_csv("reliance_product.csv", index=False)
            print("\n[✓] Data saved to reliance_product.csv")
        else:
            print("[✘] No data found.")