# Item Price Checker

Bulk-checks a list of products against live web search results to find the closest matching listing and its price.

## What It Does

`browser_agent.py` reads a list of products from an Excel file (expected columns: `GeM Product ID`, `GeM Title`, `GeM Brand`, `GeM Model` — this project appears to target GeM/government-procurement product listings, matched against open-market prices) and, for each row:

1. Builds a search query from the product's model and title.
2. Opens a real Chrome browser (via `undetected-chromedriver`) and runs a Google search for that query, to avoid basic bot-detection blocks.
3. Visits the top 3 organic results and extracts each page's title (and an `h1`, if present).
4. Compares the found title against the product's title/brand using simple token-overlap logic to classify the result as `exact`, `similar` (flagged for human review), or no match.
5. Extracts a price from the page text with a regex looking for `₹`/`INR`/`Rs` amounts.
6. Writes one row per product to an output `.xlsx` file (progress is also saved every 5 rows to a `_temp.xlsx` file), including match type, review flag, found title, price, and link.

The class also contains fully-implemented `search_amazon` and `search_flipkart` methods (site-specific scraping of Amazon.in and Flipkart search results), but **only `search_google` is currently wired into `process_products()`** — the Amazon/Flipkart search paths exist in the code but are not called from the main flow.

Running the script directly (`python browser_agent.py`) prompts interactively for an input Excel path and an output file name; there is no non-interactive/CLI-argument mode.

## Tech Stack

- Python 3
- [`undetected-chromedriver`](https://github.com/ultrafunkamsterdam/undetected-chromedriver) + `selenium` (browser automation)
- `pandas` + `openpyxl` (reading/writing Excel files)
- Standard library: `re`, `logging`, `random`, `time`, `urllib.parse`

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows PowerShell

pip install -r requirements.txt
```

You also need a local install of Google Chrome, since the script drives a real, visible Chrome window.

## Usage

```bash
python browser_agent.py
```

You'll be prompted for:
- The path to an input `.xlsx` file with columns `GeM Product ID`, `GeM Title`, `GeM Brand`, `GeM Model` (falls back to positional columns 0-3 if those headers aren't found).
- An output file name (defaults to `agent_results.xlsx`, written under `outputs/`).

Do not close the Chrome window the script opens — it drives that window directly and adds randomized delays (2-6s) between actions to look human. Logs are written per-run to `logs/browser_agent_search_<timestamp>.log`.

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```

## Status: Work in progress

This is a functional prototype with real gaps:

- **Amazon and Flipkart scraping is implemented but dead code.** `search_amazon` and `search_flipkart` are complete methods with their own XPath selectors and match logic, but `process_products()` only calls `search_google`. It's unclear whether they were deprecated in favor of Google-only search or just not yet wired in.
- **No sample input file is included.** The README previously referenced a `sample_products.xlsx`, but no such file exists in the repository, so there's nothing to run the script against out of the box.
- **Fragile scraping selectors.** The Amazon/Flipkart/Google matching all rely on specific CSS classes and XPath expressions (e.g. Flipkart's `_30jeq3`, `_1AtVbE`) that change frequently on real sites and are not covered by any error recovery beyond generic try/except-and-skip.
- **Tests only cover the matching logic.** `tests/test_match_quality.py` unit-tests `_get_match_quality` in isolation; the browser-driving code (`search_amazon`, `search_flipkart`, `search_google`, `process_products`) has no automated coverage since it requires a real Chrome session.

In short: the core Google-search-and-match pipeline is present and reasonably careful (retry-free error handling around each site call, human-like delays, incremental progress saves), but the Amazon/Flipkart code paths are unused.
