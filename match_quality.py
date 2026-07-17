"""Pure title/brand match-quality logic, kept dependency-free.

Split out of browser_agent.py so this logic can be unit tested without
installing selenium/undetected-chromedriver, which browser_agent.py pulls in
at import time just to drive an actual Chrome session.
"""
import re


def get_match_quality(excel_brand, excel_title, scraped_title):
    """
    Check if the scraped title from the website is an exact match,
    a similar match (needs human review), or none.
    Returns: 'exact', 'similar', or 'none'
    """
    base_clean = str(excel_title).lower().strip()
    scraped_clean = str(scraped_title).lower().strip()
    brand_clean = str(excel_brand).lower().strip()

    # A blank title has nothing to match against. Without this guard, an
    # empty string is a substring of everything, and 'nan' (str(float('nan')))
    # is a substring of common words like 'banana' or 'financial', so a
    # blank GeM Title would falsely report 'exact' for any scraped title.
    if base_clean in ('', 'n/a', 'nan'):
        return 'none'

    # 1. Explicit substring match -> EXACT
    if base_clean in scraped_clean:
        return 'exact'

    # Tokenize words
    base_words = set(re.findall(r'\w+', base_clean))
    scraped_words = set(re.findall(r'\w+', scraped_clean))

    # Exclude very common small words
    stop_words = {'with', 'a', 'an', 'the', 'and', 'for', 'of', 'in'}
    base_words = base_words - stop_words

    # 2. Token subset match (do all core words from excel exist in scraped title?) -> EXACT
    if base_words and base_words.issubset(scraped_words):
        return 'exact'

    # 3. Check for SIMILAR match
    # If it doesn't match perfectly, but the brand matches and at least some key words match
    #
    # Numbers (model numbers, storage sizes, screen sizes, etc.) are the most
    # distinguishing part of a product title. Word-overlap ratio alone would
    # call 'iPhone 13 Pro Max 128GB' a match for 'iPhone 14 Pro Max 128GB'
    # since only one word out of five differs. If the excel title has a
    # standalone number that's missing from the scraped title, treat it as a
    # different product rather than exact/similar.
    base_numbers = {w for w in base_words if w.isdigit()}
    scraped_numbers = {w for w in scraped_words if w.isdigit()}
    if base_numbers and not base_numbers.issubset(scraped_numbers):
        return 'none'
    #
    # Brand is matched by whole word, not raw substring: a plain `in` check
    # would let e.g. brand 'Asus' falsely match a scraped title containing
    # 'Pegasus' (which contains the substring 'asus'), same as the 'nan'
    # substring issue this file already guards against for blank cells.
    if brand_clean not in ('n/a', 'nan', ''):
        brand_words = set(re.findall(r'\w+', brand_clean))
        brand_in_scraped = brand_words.issubset(scraped_words)
    else:
        brand_in_scraped = False

    # How many significant words overlap?
    word_intersection = base_words.intersection(scraped_words)

    # If the brand matches, and we share at least 2 other significant words, consider it "similar"
    # Or if we share at least 30% of the significant words for Google results since titles are truncated
    if len(base_words) > 0:
        match_ratio = len(word_intersection) / len(base_words)

        # Very lenient similarity check so we don't miss products
        if (brand_in_scraped and len(word_intersection) >= 2) or (match_ratio >= 0.3):
            # Also if the match ratio is higher, call it exact if > 70% to avoid human review for everything
            if match_ratio >= 0.6:
                return 'exact'
            return 'similar'

    return 'none'
