from scrapers.flipkart import fetch_flipkart_products

def main():
    query = "iphone 14 pro max"
    results = fetch_flipkart_products(query, max_results=3)

    for i, product in enumerate(results, 1):
        print(f"\nProduct {i}:")
        print(f"Title : {product['title']}")
        print(f"Price : ₹{product['price']}")
        print(f"Rating: {product['rating']}")
        print(f"URL   : {product['url']}")

if __name__ == "__main__":
    main()
