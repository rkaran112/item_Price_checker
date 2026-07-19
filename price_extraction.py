"""Pure price-extraction logic, kept dependency-free.

Split out of browser_agent.py's search_google price-scraping step, the same
way match_quality.py was split out, so this regex can be unit tested without
installing selenium.
"""
import re

_PRICE_RE = re.compile(r'(?:₹|INR|Rs\.?)\s*([\d,]+(?:\.\d+)?)', re.IGNORECASE)


def extract_price(text):
    """
    Find the first Rupee amount (prefixed by ₹, INR, or Rs/Rs.) in the given
    text and return it as a '₹<amount>' string, or 'N/A' if none is found.
    """
    match = _PRICE_RE.search(text)
    if not match:
        return 'N/A'
    return f"₹{match.group(1)}"
