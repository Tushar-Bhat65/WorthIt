import time
import re
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_price(price_text):
    """Extracts numerical price from a string."""
    if not price_text:
        return None
    price_text = str(price_text)
    numbers = re.findall(r'[\d,]+\.?\d*', price_text)
    if numbers:
        return float(numbers[0].replace(',', ''))
    return None


def normalize_text(text: str) -> str:
    """Normalize text by lowercasing and removing extra spaces and symbols."""
    return re.sub(r"[^\w\s]", "", text.lower()).strip()


def is_strict_match(query: str, title: str) -> bool:
    query_words = set(normalize_text(query).split())
    title_cleaned = normalize_text(title)

    disallowed_keywords = {
        "pro", "plus", "max", "ultra", "promax", "pro max", "mini"
    }
    accessory_keywords = {
        "case", "cover", "protector", "charger", "cable", "adapter",
        "tempered", "screen guard", "screen protector", "back", "hard", "soft"
    }

    title_words = set(title_cleaned.split())
    extra_words = title_words - query_words

    if any(word in extra_words for word in disallowed_keywords):
        return False
    if any(word in title_words for word in accessory_keywords):
        return False

    return query_words.issubset(title_words)


def fetch_poorvika_html(query: str) -> str | None:
    print(f"[1] Searching for: {query}")
    html = None
    driver = None

    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("user-agent=Mozilla/5.0")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 5)

        driver.get("https://www.poorvikamobile.com/")
        print("[✓] Homepage loaded")

        try:
            body = driver.find_element(By.TAG_NAME, 'body')
            body.send_keys(Keys.ESCAPE)
            print("[✓] Escape key sent")
        except:
            print("[✓] No popup to dismiss")

        print("[✓] Locating search bar...")
        search_input = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//input[@placeholder='Search for Products, Brands, Offers']"))
        )
        search_input.clear()
        search_input.send_keys(query)

        print("[✓] Clicking search button...")
        search_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.app-bar_search_desktop__BRcZg"))
        )
        driver.execute_script("arguments[0].click();", search_button)

        print("[✓] Waiting for results...")
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "product-cardlist_card__description__eduH5")))
        html = driver.page_source
        print("[✓] Page loaded")

    except Exception as e:
        print(f"[✘] An error occurred: {e}")
    finally:
        if driver:
            driver.quit()
            print("[✓] Browser closed")

    return html


def parse_poorvika_html(html: str, query: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.product-cardlist_card__description__eduH5")
    if not cards:
        print("[✘] No product containers found.")
        return []

    results = []
    for card in cards:
        title_tag = card.find("b")
        price_tag = card.select_one("div.product-cardlist_price__1aKwZ span")
        rating_tag = card.select_one("div.product-cardlist_price__1aKwZ svg + b")
        url_tag = card.find("a", href=True)

        if not (title_tag and price_tag and url_tag):
            continue

        title = title_tag.get_text(strip=True)
        if not is_strict_match(query, title):
            continue

        price = extract_price(price_tag.get_text(strip=True))
        rating = rating_tag.get_text(strip=True) if rating_tag else "Not Available"
        url = "https://www.poorvika.com" + url_tag["href"]

        if price:
            results.append({
                "title": title,
                "price": price,
                "rating": rating,
                "url": url
            })

    results.sort(key=lambda x: x["price"])
    return results


def get_cheapest_poorvika_product(query: str):
    start_time = time.time()  # ⏳ Start timer

    html = fetch_poorvika_html(query)
    if not html:
        print("[✘] Could not retrieve HTML.")
        return

    results = parse_poorvika_html(html, query)
    if not results:
        print("No matching smartphones found.")
        return

    best = results[0]
    elapsed = time.time() - start_time  # ⏳ End timer

    print("\n--- Cheapest Exact Match on Poorvika ---")
    print(f"₹{best['price']}")
    print(f"{best['title']}")
    print(f"Rating: {best['rating']}")
    print(f"URL: {best['url']}")
    print(f"[⏱] Time taken: {elapsed:.2f} seconds")

    return best


if __name__ == "__main__" or "__file__" not in globals():
    product_name = input("Enter product name (e.g. 'iPhone 16'): ").strip()
    if product_name:
        get_cheapest_poorvika_product(product_name)
