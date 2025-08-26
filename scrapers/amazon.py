import re
import asyncio
import time
from typing import Optional, Dict, Any, List
from playwright.async_api import async_playwright, Browser, Route, Request

# --- CONFIG ---
HARD_ACCESSORY_KEYWORDS = {
    'case', 'cover', 'charger', 'cable', 'glass', 'tempered', 'protector',
    'adapter', 'earbuds', 'headphones', 'earphones', 'screen', 'screenprotector',
    'backcover', 'back', 'back-cover', 'skin', 'spare', 'replacement', 'parts'
}
VARIANT_KEYWORDS = {"pro", "max", "lite", "plus", "e", "se", "ultra", "mini", "fe", "promax"}
COMMON_STOPWORDS = {
    'mobile', 'phone', 'with', 'and', 'works', 'for', 'the', 'in', 'a', 'an',
    'new', 'smartphone', 'dual', 'sim', 'edition', 'version', 'model', 'capacity',
    'cellular', 'unlocked', 'brand', 'only', 'available'
}
COLOR_KEYWORDS = {
    'black', 'white', 'red', 'blue', 'green', 'yellow', 'gold', 'silver',
    'titanium', 'natural', 'desert', 'pink', 'purple', 'graphite', 'space', 'grey', 'gray', 'teal', 'ultramarine'
}
STORAGE_RE = re.compile(r'\b\d+(\.\d+)?\s*(gb|tb|mb)\b', flags=re.I)

# --- HELPERS ---

# Helper functions (make sure these exist in your file)
def clean_price(text: str) -> Optional[int]:
    import re
    if not text:
        return None
    groups = re.findall(r'\d[\d,\.]*', text)
    if not groups:
        return None
    best = max(groups, key=lambda s: len(re.sub(r'[^0-9]', '', s)))
    num = re.sub(r'[^\d]', '', best)
    return int(num) if num else None


def normalize(s: str) -> str:
    import re
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokenize(s: str) -> List[str]:
    return [w for w in s.split() if w]

HARD_ACCESSORY_KEYWORDS = {'case', 'cover', 'charger', 'cable', 'glass', 'tempered',
                           'protector', 'adapter', 'earbuds', 'headphones', 'earphones',
                           'screen', 'screenprotector', 'backcover', 'back', 'back-cover',
                           'skin', 'spare', 'replacement', 'parts'}

VARIANT_KEYWORDS = {"pro", "max", "lite", "plus", "e", "se", "ultra", "mini", "fe", "promax"}

COMMON_STOPWORDS = {'mobile', 'phone', 'with', 'and', 'works', 'for', 'the', 'in', 'a', 'an',
                    'new', 'smartphone', 'dual', 'sim', 'edition', 'version', 'model', 'capacity',
                    'cellular', 'unlocked', 'brand', 'only', 'available'}

COLOR_KEYWORDS = {'black', 'white', 'red', 'blue', 'green', 'yellow', 'gold', 'silver',
                  'titanium', 'natural', 'desert', 'pink', 'purple', 'graphite', 'space',
                  'grey', 'gray', 'teal', 'ultramarine'}

import re
STORAGE_RE = re.compile(r'\b\d+(\.\d+)?\s*(gb|tb|mb)\b', flags=re.I)


def is_relevant(query: str, title: str, price: Optional[int]) -> (bool, str):
    if not title or not query:
        return (False, "Title or query is empty")
    q_norm = normalize(query)
    t_norm = normalize(title)
    t_norm = STORAGE_RE.sub(" ", t_norm)
    query_words = tokenize(q_norm)
    title_words = tokenize(t_norm)
    if price and price < 5000:
        return (False, f"Price too low: ₹{price}")
    hw_in_title = [k for k in HARD_ACCESSORY_KEYWORDS if k in title_words]
    if hw_in_title and not all(q in title_words for q in query_words):
        return (False, f"Accessory keyword(s): {', '.join(hw_in_title)}")
    filtered = [w for w in title_words if w not in COMMON_STOPWORDS and w not in COLOR_KEYWORDS and not (w.isdigit() and len(w) >= 4)]
    if any(q not in filtered for q in query_words):
        return (False, "Missing query word")
    query_variants = set(q for q in query_words if q in VARIANT_KEYWORDS)
    title_variants = set(w for w in filtered if w in VARIANT_KEYWORDS)
    if query_variants:
        if title_variants - query_variants:
            return (False, "Extra variant found")
    return (True, "Match")


class AmazonScraper:
    def __init__(self):
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context = None

    async def start(self, headless: bool = True):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=headless, args=["--no-sandbox"])
        self.context = await self.browser.new_context(
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"),
            locale="en-IN"
        )
        await self.context.route("**/*", self._block_resources)

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def _block_resources(self, route: Route, request: Request):
        blocked_types = {"image", "stylesheet", "font", "media"}
        blocked_scripts = [
            "tracking", "analytics", "pixel", "adsystem", "google-analytics", "doubleclick"
        ]
        url = request.url.lower()
        if request.resource_type in blocked_types or any(b in url for b in blocked_scripts):
            await route.abort()
        else:
            await route.continue_()

    async def scrape_amazon(self, query: str, max_items: int = 6, timeout: int = 15000) -> Dict[str, Any]:
        page = await self.context.new_page()
        try:
            await page.goto(
                f"https://www.amazon.in/s?k={query.replace(' ', '+')}",
                wait_until="domcontentloaded",
                timeout=timeout
            )
            await page.wait_for_selector("div.s-main-slot", state="attached", timeout=4000)

            raw_products = await page.evaluate(f"""
            () => {{
                const items = Array.from(document.querySelectorAll("div[data-component-type='s-search-result']")).slice(0, {max_items});
                return items.map(item => {{
                    const titleEl = item.querySelector("h2 span");
                    const priceEl = item.querySelector("span.a-offscreen");
                    const ratingEl = item.querySelector("span.a-icon-alt");
                    const linkEl = item.querySelector("a.a-link-normal[href*='/dp/'], a[href*='/gp/']");
                    return {{
                        title: titleEl ? titleEl.innerText.trim() : null,
                        priceText: priceEl ? priceEl.innerText : null,
                        ratingText: ratingEl ? ratingEl.innerText : null,
                        url: linkEl ? linkEl.href : null
                    }};
                }});
            }}
            """)

            relevant = [
                {
                    "title": p["title"],
                    "price": clean_price(p["priceText"]),
                    "rating": p["ratingText"].split()[0] if p["ratingText"] else None,
                    "url": p["url"] if p["url"] else f"https://www.amazon.in/s?k={query.replace(' ', '+')}"
                }
                for p in raw_products
                if p["title"] and is_relevant(query, p["title"], clean_price(p["priceText"]))[0]
            ]

            valid_relevant = [p for p in relevant if p["price"] is not None]

            if valid_relevant:
                return min(valid_relevant, key=lambda x: x["price"])
            elif relevant:
                return relevant[0]
            else:
                return {}
        finally:
            await page.close()

# --- Exported Function for Backend ---
_scraper_instance: Optional[AmazonScraper] = None

async def fetch_amazon_product(query: str) -> Dict[str, Any]:
    global _scraper_instance
    if _scraper_instance is None:
        _scraper_instance = AmazonScraper()
        await _scraper_instance.start(headless=True)
    return await _scraper_instance.scrape_amazon(query)

# --- Optional Demo ---
if __name__ == "__main__":
    async def main():
        query = input("Enter product name: ").strip()
        start_time = time.time()
        result = await fetch_amazon_product(query)
        print(result or "No relevant products found.")
        print(f"⏱ Time: {time.time() - start_time:.2f}s")
    asyncio.run(main())

# Backward compatibility for old backend
scrape_amazon = fetch_amazon_product
