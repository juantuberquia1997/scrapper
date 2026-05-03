# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install requests openpyxl tqdm

# Discover available collection handles
python site_prober.py --list-collections

# Auto-detect which collections cover the frequent products list
python site_prober.py --match-collections

# Run the tracker
python site_prober.py
```

## Files

| File | Purpose |
|---|---|
| `site_prober.py` | Main script — all logic |
| `product_frequents.md` | Products the user buys frequently — drives the "Frecuente" column in Excel |

## Architecture

Single-file script. `site_prober.py` is the only source file.

**Execution flow:**
1. `main()` reads `COLLECTIONS_TO_TRACK` (or discovers all handles via sitemap if empty)
2. `scrape_collection()` fetches `/collections/{handle}/products.json?limit=250&page=N` for each collection — returns products + prices in bulk, no per-product requests
3. Collections are scraped in parallel via `ThreadPoolExecutor(max_workers=MAX_WORKERS)`
4. Products appearing in multiple collections are deduplicated by URL
5. `export_excel()` builds a 4-sheet `.xlsx` report
6. `send_email()` attaches the Excel and sends via SMTP (disabled by default)

**Key config at top of file:**
- `COLLECTIONS_TO_TRACK` — list of collection handles to scan; leave empty to scan all (~7000+ products)
- `MAX_WORKERS` — concurrent collection requests (default 3; increase carefully to avoid 429s)
- `RETRY_WAIT` / `MAX_RETRIES` — backoff config for 429 rate-limit responses
- `ENABLE_EMAIL`, `SENDER_EMAIL`, `SENDER_PASSWORD`, `RECIPIENT_EMAIL` — set via env vars to enable email

**Frequent products (`product_frequents.md`):**
- Loaded at startup by `_load_frequent_products()`
- Matching via `is_frequent(title)` uses `str.startswith` against full legacy names (not substring) to avoid false positives

**Discount detection:**
- Uses Shopify JSON API: `variant.compare_at_price > variant.price` → on sale
- `variant.available` → stock status
- No HTML scraping, no CSS selectors — resilient to site redesigns

**Output:** `supermu_descuentos_YYYYMMDD_HHMMSS.xlsx` with 4 sheets:
- `Con Descuento` — discounted products with stock, sorted by savings %
- `Descuento Sin Stock` — discounted but out of stock
- `Todos los Resultados` — full catalog with Frecuente / Disponible / Estado columns
- `Resumen` — summary counts

## Automation (Windows Task Scheduler)

```cmd
schtasks /create /tn "SupermuScraper" /tr "python C:\Users\1234\Documents\github\scrapper\site_prober.py" /sc daily /st 07:00
```
