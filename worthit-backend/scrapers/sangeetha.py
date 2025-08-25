import time
import logging
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd

# Configure logging
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

def scrape_sangeetha_product(query: str):
    logger.info(f"[Sangeetha Scraper] Starting search for: '{query}'")
    total_start = time.time()

    page_source = None
    driver = None
    try:
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_argument(
            'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
        )
        options.add_argument("--blink-settings=imagesEnabled=false")  # disable images
        options.page_load_strategy = 'none'  # fast load strategy

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 10)

        start_homepage = time.time()
        driver.get("https://www.sangeethamobiles.com/")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input.search__home")))
        homepage_load_time = time.time() - start_homepage
        logger.info(f"Homepage loaded in {homepage_load_time:.2f} seconds.")

        try:
            short_wait = WebDriverWait(driver, 2)
            bengaluru_button = short_wait.until(
                EC.visibility_of_element_located((By.XPATH, "//div[@id='staticBackdrop']//button[contains(text(), 'Bengaluru')]"))
            )
            driver.execute_script("arguments[0].click();", bengaluru_button)
            logger.info("City pop-up dismissed.")
        except Exception:
            logger.info("City pop-up did not appear. Continuing...")

        search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input.search__home")))
        search_input.clear()
        search_input.send_keys(query)
        search_input.send_keys(Keys.ENTER)
        logger.info("Search submitted.")

        wait.until(EC.url_contains("search-result"))
        time.sleep(3)  # let full content load after navigation

        page_source = driver.page_source
        logger.info("Successfully loaded results page.")

    except Exception as e:
        logger.error(f"An error occurred during browser navigation: {e}")
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed.")

    if not page_source:
        logger.error("Failed to retrieve final page source.")
        return None

    # --- PARSING PHASE from your older code ---
    logger.info("[Parser] Parsing the retrieved HTML.")
    soup = BeautifulSoup(page_source, "html.parser")
    product_containers = soup.select("div.product-list")

    if not product_containers:
        logger.warning("Could not find any product containers.")
        return None

    logger.info(f"Found {len(product_containers)} product(s). Searching for the most relevant one...")

    query_words = {word.lower() for word in query.split()}

    for container in product_containers:
        title_tag = container.select_one("div.product-details h2")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        title_words = {word.lower() for word in title.split()}

        if query_words.issubset(title_words):
            logger.info(f"Found a matching product: {title}")

            price_tag = container.select_one("div.new-price-1")
            url_tag = container.select_one("a[href]")

            price = extract_price(price_tag.get_text(strip=True)) if price_tag else "Not Available"
            rating = "Not Available"

            url = f"https://www.sangeethamobiles.com{url_tag['href']}" if url_tag and url_tag.has_attr('href') else "Not Available"

            total_elapsed = time.time() - total_start
            logger.info(f"Total scraping time: {total_elapsed:.2f} seconds.")

            return {
                "title": title,
                "price": price,
                "rating": rating,
                "url": url
            }

    logger.warning(f"Could not find a product matching the query '{query}'")
    return None


if __name__ == '__main__':
    product_to_search = input("What product would you like to search for on SangeethaMobiles.com? ").strip()

    if product_to_search:
        scraped_data = scrape_sangeetha_product(product_to_search)

        if scraped_data:
            print("\n--- Scraped Product Data ---")
            print(f"  Title: {scraped_data['title']}")
            print(f"  Price: {scraped_data['price']}")
            print(f"  Rating: {scraped_data['rating']}")
            print(f"  URL: {scraped_data['url']}")

            df = pd.DataFrame([scraped_data], columns=['title', 'price', 'rating', 'url'])
            df.to_csv("sangeetha_product.csv", index=False)
            print("\nData saved to sangeetha_product.csv")
        else:
            print("No matching product found.")
