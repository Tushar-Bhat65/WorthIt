# test_croma.py

from scrapers.croma import fetch_croma_products

def main():
    query = "iPhone 16"
    results = fetch_croma_products(query)

    for i, item in enumerate(results, start=1):
        print(f"\nProduct {i}:")
        print("Title :", item['title'])
        print("Price :", item['price'])
        print("Rating:", item['rating'])
        print("URL   :", item['url'])

if __name__ == "__main__":
    main()
