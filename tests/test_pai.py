from scrapers.pai import fetch_pai_products

def main():
    query = "samsung s25 ultra"
    results = fetch_pai_products(query)
    for idx, product in enumerate(results, start=1):
        print(f"\nProduct {idx}:")
        print(f"Title : {product['title']}")
        print(f"Price : {product['price']}")
        print(f"URL   : {product['url']}")

if __name__ == "__main__":
    main()
