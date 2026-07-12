"""Unit tests for BrowserAgentChecker._get_match_quality.

This is the only piece of pure matching logic in browser_agent.py; everything
else drives a real Chrome browser. We call it as an unbound method so we don't
have to spin up undetected-chromedriver just to exercise the string matching.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from browser_agent import BrowserAgentChecker

match_quality = BrowserAgentChecker._get_match_quality


def test_exact_via_substring():
    assert match_quality(None, 'Samsung', 'Samsung Galaxy Watch',
                          'Samsung Galaxy Watch 6 Pro - Amazon.in') == 'exact'


def test_exact_via_token_subset():
    assert match_quality(None, 'N/A', 'Blue Widget',
                          'Widget in Blue Color Available Now') == 'exact'


def test_similar_match_low_ratio_with_brand():
    result = match_quality(
        None, 'Samsung', 'Samsung 55 inch 4K Smart TV',
        'Samsung 55" Class Television Deals',
    )
    assert result == 'similar'


def test_upgraded_to_exact_when_ratio_high():
    result = match_quality(None, 'N/A', 'red blue green yellow black',
                            'red blue green yellow purple')
    assert result == 'exact'


def test_no_match():
    assert match_quality(None, 'N/A', 'apple watch', 'banana bread recipe') == 'none'


def test_blank_brand_does_not_false_match_via_nan_substring():
    """Regression test for the false brand match from a blank GeM Brand cell.

    str(float('nan')) == 'nan', and 'nan' is a substring of common words like
    'nano'. A blank brand must not be treated as matching just because the
    scraped title happens to contain a word starting with 'nan'.
    """
    excel_brand = float('nan')
    excel_title = 'alpha beta gamma delta epsilon zeta eta'
    scraped_title = 'nano version alpha beta signal tower unit'

    assert match_quality(None, excel_brand, excel_title, scraped_title) == 'none'


def test_blank_brand_string_variants_excluded():
    for blank in ('n/a', 'nan', ''):
        assert match_quality(None, blank, 'alpha beta gamma delta epsilon zeta eta',
                              'nano version alpha beta signal tower unit') == 'none'


def test_blank_title_does_not_false_match_everything():
    """Regression test for a blank GeM Title matching any scraped title.

    An empty excel_title makes '' a substring of every scraped title, and
    str(float('nan')) == 'nan' is a substring of common words like 'banana'.
    Either way a blank title must not be reported as an 'exact' match.
    """
    assert match_quality(None, 'N/A', '', 'totally unrelated random webpage title') == 'none'
    assert match_quality(None, 'N/A', float('nan'), 'banana bread recipe website') == 'none'


def test_blank_title_string_variants_excluded():
    for blank in ('n/a', 'nan', ''):
        assert match_quality(None, 'N/A', blank, 'banana bread recipe website') == 'none'
