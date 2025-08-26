from scrapers.poorvika import fetch_poorvika_products

def main():
    query = "iPhone 16"
    results = fetch_poorvika_products(query)
    for idx, product in enumerate(results, 1):
        print(f"\nProduct {idx}:")
        print("Title :", product["title"])
        print("Price :", product["price"])
        print("Rating:", product["rating"])
        print("URL   :", product["url"])

if __name__ == "__main__":
    main()
