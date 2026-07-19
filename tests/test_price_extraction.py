"""Unit tests for price_extraction.extract_price."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from price_extraction import extract_price


def test_extracts_rupee_symbol_amount():
    assert extract_price('Price: ₹1,299 - In stock') == '₹1,299'


def test_extracts_decimal_amount():
    assert extract_price('Total: Rs. 1,299.99 including tax') == '₹1,299.99'


def test_extracts_inr_prefix():
    assert extract_price('Cost is INR 4500 for this item') == '₹4500'


def test_no_price_returns_na():
    assert extract_price('No pricing information available here') == 'N/A'


def test_does_not_capture_trailing_sentence_punctuation():
    """Regression test for a trailing period being swept into the price.

    The old regex used a character class of [\\d,.] for the whole amount,
    so a sentence-ending period right after the price (e.g. 'Rs. 1200. Free
    shipping') was captured as part of the number, producing '1200.'
    instead of '1200'.
    """
    assert extract_price('Buy now Rs. 1200. Free shipping available today') == '₹1200'
