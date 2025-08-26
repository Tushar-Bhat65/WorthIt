import re

def clean_price(price_str):
    """
    Cleans a price string like "₹75,999.00" → 75999 (int)
    """
    if not price_str:
        return None
    # Remove non-numeric characters
    digits = re.sub(r"[^\d]", "", price_str)
    return int(digits) if digits else None
