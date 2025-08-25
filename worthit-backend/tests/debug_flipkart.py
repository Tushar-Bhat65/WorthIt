from scrapers.flipkart import fetch_flipkart_products

def main():
    query = "iphone 16 pro max 512gb"
    print(f"Searching Flipkart for: {query}\n")

    products = fetch_flipkart_products(query, max_results=1)
    for idx, p in enumerate(products, 1):
        print(f"Result {idx}:")
        print(f"  Title : {p['title']}")
        print(f"  Price : ₹{p['price']}")
        print(f"  Rating: {p['rating']}")
        print(f"  URL   : {p['url']}\n")

if __name__ == "__main__":
    main()
