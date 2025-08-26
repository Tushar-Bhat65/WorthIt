# test_fetch.py

from utils.http import fetch_html

def main():
    url = "https://www.amazon.in/s?k=iphone+14"
    print(f"Fetching HTML for: {url}\n")
    
    html = fetch_html(url)
    # Print just the first 500 characters so we can verify it worked
    print(html[:500])

if __name__ == "__main__":
    main()
