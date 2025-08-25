import re

def extract_price(text: str):
    """Extracts numeric price from text like '₹1,29,999.00'."""
    try:
        numbers = re.findall(r'\d+', text.replace(',', ''))
        if not numbers:
            return None
        return int(''.join(numbers))
    except:
        return None

def is_exact_match(query: str, title: str) -> bool:
    """Checks if all keywords from query exist in title (case-insensitive, word-wise)."""
    query_words = query.lower().split()
    title_words = title.lower()
    return all(word in title_words for word in query_words)
