# testall.py

from scrapers.amazon import fetch_amazon_products
from scrapers.flipkart import fetch_flipkart_products
from scrapers.croma import fetch_croma_products
from scrapers.reliance import scrape_reliance_product  # ✅ fixed function name
from scrapers.poorvika import fetch_poorvika_products
from scrapers.pai import fetch_pai_products
from scrapers.sangeetha import scrape_sangeetha_product

def format_product(product):
    if not product:
        return "No product found.\n"
    return (
        f"Price: ₹{product['price']}\n"
        f"Rating: {product.get('rating', 'N/A')}\n"
        f"URL: {product['url']}\n"
    )

def get_cheapest(products):
    if not products:
        return None
    return min(products, key=lambda p: p['price'] if isinstance(p['price'], (int, float)) else float('inf'))

def safe_fetch(scraper_func, query, name):
    try:
        if name in ["Sangeetha", "Reliance Digital"]:
            result = scraper_func(query)
            return result
        else:
            results = scraper_func(query)
            return get_cheapest(results)
    except Exception as e:
        return {"error": str(e)}

def main():
    query = input("Enter product to search: ").strip()
    if not query:
        print("Please enter a valid query.")
        return

    scrapers = [
        ("Amazon", fetch_amazon_products),
        ("Flipkart", fetch_flipkart_products),
        ("Croma", fetch_croma_products),
        ("Reliance Digital", scrape_reliance_product),  # ✅ fixed here
        ("Poorvika", fetch_poorvika_products),
        ("Pai International", fetch_pai_products),
        ("Sangeetha", scrape_sangeetha_product),
    ]

    print(f"\n🔍 Searching for: **{query}**\n{'=' * 60}")

    for name, scraper_func in scrapers:
        print(f"\n{name}:")
        result = safe_fetch(scraper_func, query, name)
        if result is None:
            print("No product found.")
        elif isinstance(result, dict) and "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(format_product(result))

if __name__ == "__main__":
    main()
