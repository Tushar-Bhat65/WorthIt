# test_amazon.py

from scrapers.amazon_phase1 import open_amazon_search_page
from scrapers.amazon_phase2 import extract_amazon_results

query = "iphone 16 pro max 256 GB"

open_amazon_search_page(query, headless=False)  # Save HTML using browser
results = extract_amazon_results(query, max_results=3)

for i, product in enumerate(results, 1):
    print(f"\n[{i}] ₹{product['price']} — {product['rating']}")
    print(product["url"])
