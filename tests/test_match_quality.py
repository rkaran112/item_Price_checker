"""Unit tests for match_quality.get_match_quality.

This is the only piece of pure matching logic used by browser_agent.py;
everything else drives a real Chrome browser. It lives in its own
dependency-free module so these tests don't require installing
selenium/undetected-chromedriver just to exercise the string matching.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from match_quality import get_match_quality

match_quality = get_match_quality


def test_exact_via_substring():
    assert match_quality('Samsung', 'Samsung Galaxy Watch',
                          'Samsung Galaxy Watch 6 Pro - Amazon.in') == 'exact'


def test_exact_via_token_subset():
    assert match_quality('N/A', 'Blue Widget',
                          'Widget in Blue Color Available Now') == 'exact'


def test_similar_match_low_ratio_with_brand():
    result = match_quality(
        'Samsung', 'Samsung 55 inch 4K Smart TV',
        'Samsung 55" Class Television Deals',
    )
    assert result == 'similar'


def test_upgraded_to_exact_when_ratio_high():
    result = match_quality('N/A', 'red blue green yellow black',
                            'red blue green yellow purple')
    assert result == 'exact'


def test_no_match():
    assert match_quality('N/A', 'apple watch', 'banana bread recipe') == 'none'


def test_blank_brand_does_not_false_match_via_nan_substring():
    """Regression test for the false brand match from a blank GeM Brand cell.

    str(float('nan')) == 'nan', and 'nan' is a substring of common words like
    'nano'. A blank brand must not be treated as matching just because the
    scraped title happens to contain a word starting with 'nan'.
    """
    excel_brand = float('nan')
    excel_title = 'alpha beta gamma delta epsilon zeta eta'
    scraped_title = 'nano version alpha beta signal tower unit'

    assert match_quality(excel_brand, excel_title, scraped_title) == 'none'


def test_blank_brand_string_variants_excluded():
    for blank in ('n/a', 'nan', ''):
        assert match_quality(blank, 'alpha beta gamma delta epsilon zeta eta',
                              'nano version alpha beta signal tower unit') == 'none'


def test_blank_title_does_not_false_match_everything():
    """Regression test for a blank GeM Title matching any scraped title.

    An empty excel_title makes '' a substring of every scraped title, and
    str(float('nan')) == 'nan' is a substring of common words like 'banana'.
    Either way a blank title must not be reported as an 'exact' match.
    """
    assert match_quality('N/A', '', 'totally unrelated random webpage title') == 'none'
    assert match_quality('N/A', float('nan'), 'banana bread recipe website') == 'none'


def test_blank_title_string_variants_excluded():
    for blank in ('n/a', 'nan', ''):
        assert match_quality('N/A', blank, 'banana bread recipe website') == 'none'


def test_different_model_number_does_not_false_match():
    """Regression test for word-overlap ratio ignoring a differing model number.

    'iPhone 13 Pro Max 128GB' vs 'iPhone 14 Pro Max 128GB' only differs in one
    word out of five (an 80% overlap), which the ratio-based similarity check
    alone would call 'exact'. The model number is the whole point of the
    title, so a scraped title missing it must not be treated as a match.
    """
    result = match_quality(
        'Apple', 'iPhone 13 Pro Max 128GB',
        'Apple iPhone 14 Pro Max 128GB Case Cover Buy Online',
    )
    assert result == 'none'


def test_brand_does_not_false_match_via_substring_collision():
    """Regression test for brand matching via raw substring containment.

    Brand 'Asus' is a substring of 'Pegasus', so a naive `brand in
    scraped_title` check would treat an unrelated Pegasus running-shoes page
    as sharing the brand with an Asus laptop, tipping an otherwise weak word
    overlap into a false 'similar' verdict.
    """
    result = match_quality(
        'Asus', 'Asus ROG Strix G15 Gaming Laptop Computer',
        'Pegasus Laptop Computer Store Reviews Today Now',
    )
    assert result == 'none'
