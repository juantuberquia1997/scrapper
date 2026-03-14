# Supermu Discount Tracker

Scrapes [supermu.com](https://supermu.com) and reports which products from your tracking list have active discounts or promotions. Results are exported to an Excel file.

---

## Files

| File | Purpose |
|---|---|
| `site_prober.py` | **Main script** — run this. Contiene la lista de productos y toda la lógica |

---

## How to Run

```bash
python site_prober.py
```

The script will search each product, print progress in the terminal, and save an Excel report when done.

---

## How to Add or Remove Products

Open `site_prober.py` and edit the `PRODUCTS_TO_TRACK` list al inicio del archivo:

```python
PRODUCTS_TO_TRACK = [
    "CEBOLLA ROJA",
    "ARROZ DIANA 1000 G",
    # add or remove products here
]
```

> Use the product name as it appears on the Supermu website for best results.

---

## Output

Each run generates a new Excel file named:

```
supermu_descuentos_YYYYMMDD_HHMMSS.xlsx
```

The file has 3 sheets:

| Sheet | Content |
|---|---|
| **Con Descuento** | Only products with active discounts, sorted by highest savings % |
| **Todos los Resultados** | All searched products with status (discount / no discount / not found) |
| **Resumen** | Summary counts |

---

## Requirements

Install dependencies once:

```bash
pip install requests beautifulsoup4 openpyxl
```

---

## How It Detects Discounts

The script parses the static HTML returned by the Supermu search page. For each product it checks:

1. `.collection-discount-tag` / `.daily-discount-tag` — primary discount block
   - Extracts `.discount-price-original`, `.discount-price-final`, `.discount-percent-label`
   - If the original price is missing from the tag, it falls back to `span[data-js-product-price] span`
   - If the final price is missing, it calculates it from the percentage in the label (e.g. "Ahorro 20%")
2. `.label--sale` — fallback badge (records the label only, no price data)
