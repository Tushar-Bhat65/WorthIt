from scrapers.sangeetha import fetch_sangeetha_products

if __name__ == "__main__":
    query = "iPhone 16"
    results = fetch_sangeetha_products(query)

    for idx, product in enumerate(results, start=1):
        print(f"\nProduct {idx}:")
        print(f"Title : {product['title']}")
        print(f"Price : {product['price']}")
        print(f"Rating: {product['rating']}")
        print(f"URL   : {product['url']}")
