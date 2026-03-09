# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install requests beautifulsoup4 openpyxl

# Run the scraper
python site_prober.py
```

## Architecture

Single-file script: `site_prober.py` is the only source file.

**Execution flow:**
1. `main()` iterates over `PRODUCTS_TO_TRACK`, calling `search_product()` for each
2. `search_product()` makes one HTTP GET to `https://supermu.com/search?q=<term>`, parses the first `<product-item>` element, and extracts discount data from `.daily-discount-tag` (or falls back to `.label--sale`)
3. After all products are checked, `export_excel()` builds a 3-sheet `.xlsx` report
4. `send_email()` attaches the Excel and sends it via SMTP (disabled by default)

**Key config at top of file:**
- `PRODUCTS_TO_TRACK` — list of product names to search (edit here to add/remove)
- `ENABLE_EMAIL`, `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAIL` — set these to enable daily email delivery

**Output:** `supermu_descuentos_YYYYMMDD_HHMMSS.xlsx` saved in the working directory.

**HTML selectors used** (may break if Supermu redesigns):
- `product-item` — container for each search result
- `div.acciones[data-product-title]` / `[data-product-url]` — title and URL
- `.daily-discount-tag` → `.discount-price-original`, `.discount-price-final`, `.discount-percent-label`
- `.label--sale` — fallback badge
- `span[data-js-product-price] span` — listed price when no discount

## Automation (Windows Task Scheduler)

```cmd
schtasks /create /tn "SupermuScraper" /tr "python C:\Users\1234\Desktop\scrapper\site_prober.py" /sc daily /st 07:00
```
