# Supermu Discount Tracker

Scrapes [supermu.com](https://supermu.com) and reports which products from your tracking list have active discounts or promotions. Results are exported to an Excel file.

---

## Files

| File | Purpose |
|---|---|
| `site_prober.py` | **Main script** — run this |
| `supermu_scraper.py` | Product list configuration |

---

## How to Run

```bash
python site_prober.py
```

The script will search each product, print progress in the terminal, and save an Excel report when done.

---

## How to Add or Remove Products

Open `supermu_scraper.py` and edit the `PRODUCTS_TO_TRACK` list:

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
