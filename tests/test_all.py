import logging
from scrapers.amazon import fetch_amazon_products
from scrapers.flipkart import fetch_flipkart_products
from scrapers.croma import fetch_croma_products
from scrapers.reliance import fetch_reliance_products
from scrapers.poorvika import fetch_poorvika_products
from scrapers.pai import fetch_pai_products
from scrapers.sangeetha import fetch_sangeetha_products

def print_product_table(all_results):
    print("\n" + "-" * 120)
    print(f"{'Website':<20} | {'Product 1':<30} | {'Product 2':<30} | {'Product 3':<30}")
    print("-" * 120)

    for site, products in all_results.items():
        row = f"{site:<20} |"
        for i in range(3):
            if i < len(products):
                p = products[i]
                price_str = f"₹{p['price']}" if isinstance(p['price'], (int, float)) else p['price']
                label = f"{p['title'][:25]} - {price_str}"
                row += f" {label:<30} |"
            else:
                row += f" {'':<30} |"
        print(row)
    print("-" * 120 + "\n")

def fetch_all(product_name):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("fetch_all")
    logger.info(f"Fetching all sites for query: {product_name}")

    all_results = {}

    # Amazon
    try:
        from utils.http import random_sleep
    except ImportError:
        import time, random
        def random_sleep(): time.sleep(random.uniform(2, 5))

    try:
        from scrapers.amazon import fetch_amazon_products
        products = fetch_amazon_products(product_name)
        sorted_products = sorted(products, key=lambda x: x["price"] or float('inf'))
        all_results["Amazon"] = sorted_products[:3]
    except Exception as e:
        all_results["Amazon"] = []
        logger.warning(f"[Amazon] Error: {e}")

    # Flipkart
    try:
        products = fetch_flipkart_products(product_name)
        sorted_products = sorted(products, key=lambda x: x["price"] or float('inf'))
        all_results["Flipkart"] = sorted_products[:3]
    except Exception as e:
        all_results["Flipkart"] = []
        logger.warning(f"[Flipkart] Error: {e}")

    # Croma
    try:
        products = fetch_croma_products(product_name)
        sorted_products = sorted(products, key=lambda x: x["price"] or float('inf'))
        all_results["Croma"] = sorted_products[:3]
    except Exception as e:
        all_results["Croma"] = []
        logger.warning(f"[Croma] Error: {e}")

    # Reliance Digital
    try:
        products = fetch_reliance_products(product_name)
        sorted_products = sorted(products, key=lambda x: x["price"] or float('inf'))
        all_results["Reliance"] = sorted_products[:3]
    except Exception as e:
        all_results["Reliance"] = []
        logger.warning(f"[Reliance] Error: {e}")

    # Poorvika
    try:
        products = fetch_poorvika_products(product_name)
        sorted_products = sorted(products, key=lambda x: x["price"] or float('inf'))
        all_results["Poorvika"] = sorted_products[:3]
    except Exception as e:
        all_results["Poorvika"] = []
        logger.warning(f"[Poorvika] Error: {e}")

    # Pai International
    try:
        products = fetch_pai_products(product_name)
        sorted_products = sorted(products, key=lambda x: x["price"] or float('inf'))
        all_results["Pai"] = sorted_products[:3]
    except Exception as e:
        all_results["Pai"] = []
        logger.warning(f"[Pai] Error: {e}")

    # Sangeetha
    try:
        products = fetch_sangeetha_products(product_name)
        sorted_products = sorted(products, key=lambda x: x["price"] or float('inf'))
        all_results["Sangeetha"] = sorted_products[:3]
    except Exception as e:
        all_results["Sangeetha"] = []
        logger.warning(f"[Sangeetha] Error: {e}")

    return all_results


if __name__ == "__main__":
    query = input("Enter product name to search: ").strip()
    results = fetch_all(query)
    print_product_table(results)
