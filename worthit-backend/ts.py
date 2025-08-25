# playwright_test.py
from playwright.sync_api import sync_playwright

def run_test():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com", timeout=15_000)
        print("Title:", page.title())
        browser.close()

if __name__ == "__main__":
    run_test()
