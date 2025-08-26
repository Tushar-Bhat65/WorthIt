import requests
import random
import time
import logging
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fallback user agents in case fake_useragent breaks
FALLBACK_UAS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64)...",  # Use your own full UAs
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...",
    "Mozilla/5.0 (Linux; Android 11; Pixel 5)...",
]

def get_random_headers():
    try:
        ua = UserAgent()
        user_agent = ua.random
    except Exception:
        user_agent = random.choice(FALLBACK_UAS)

    headers = {
        "User-Agent": user_agent,
        "Accept-Language": random.choice(["en-IN,en;q=0.9", "hi-IN,hi;q=0.9"]),
        "Accept-Encoding": "gzip, deflate, br",
    }
    return headers

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(requests.exceptions.RequestException),
)
def fetch_html(url: str) -> str:
    headers = get_random_headers()

    delay = random.uniform(3, 6)
    logger.info(f"[+] Sleeping for {delay:.2f} seconds before request...")
    time.sleep(delay)

    response = requests.get(url, headers=headers, timeout=10)

    if response.status_code != 200:
        logger.warning(f"[!] Non-200 status code: {response.status_code}")
        response.raise_for_status()

    return response.text
