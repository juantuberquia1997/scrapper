# Supermu Discount Tracker

Automatically discovers all products from [supermu.com](https://supermu.com) via Shopify sitemaps, fetches prices through the Shopify JSON API, and exports a discount report to Excel.

---

## Files

| File | Purpose |
|---|---|
| `site_prober.py` | Main script — all logic lives here |
| `product_frequents.md` | List of products you buy frequently — edit this to update the "Frecuente" column in the report |

---

## Requirements

```bash
pip install requests openpyxl tqdm
```

---

## How to Run

### 1. Discover available collection handles
```bash
python site_prober.py --list-collections
```

### 2. Match your frequent products to collections
```bash
python site_prober.py --match-collections
```
Prints which collection handles cover the products in `product_frequents.md`, and generates a ready-to-paste `COLLECTIONS_TO_TRACK` block.

### 3. Set the collections to track
Open `site_prober.py` and fill in `COLLECTIONS_TO_TRACK`:

```python
COLLECTIONS_TO_TRACK = [
    "frutas-y-verduras",
    "carnes",
    "lacteos",
    "aseo-del-hogar",
]
```

> Leave it empty to scan the entire catalog (~7000+ products, takes longer).

### 4. Run the tracker
```bash
python site_prober.py
```

---

## Output

Each run saves a new Excel file:

```
supermu_descuentos_YYYYMMDD_HHMMSS.xlsx
```

| Sheet | Content |
|---|---|
| **Con Descuento** | Products with active discounts **and** stock available, sorted by highest savings % |
| **Descuento Sin Stock** | Products with active discounts but currently out of stock |
| **Todos los Resultados** | Full catalog with status, availability, and frequent flag |
| **Resumen** | Summary counts — discounts with/without stock, errors, totals |

### Columns

| Column | Description |
|---|---|
| Frecuente | `Sí` if the product is in `product_frequents.md` |
| Disponible | `Sí` / `No` — whether the product is in stock |
| Precio Original | Listed price (or compare-at price if on sale) |
| Precio con Descuento | Sale price |
| Ahorro (COP) / Ahorro (%) | Absolute and relative savings |

---

## How to Manage Frequent Products

Edit `product_frequents.md` — add or remove product names from the list. The script reads this file on every run. No code changes needed.

The matching uses `startswith` against the product's real title, so partial names work:

```
"GALLETA DUCALES NOE"  →  matches  →  "GALLETA DUCALES NOEL 200G"  ✅
```

---

## How Discounts Are Detected

The script uses the **Shopify product JSON API** (`/products/{handle}.json` or via collection API). A product is on sale when:

```
variant.compare_at_price > variant.price
```

This is more reliable than HTML scraping — no CSS selectors that break on redesigns.

---

## Automation (Windows Task Scheduler)

```cmd
schtasks /create /tn "SupermuScraper" /tr "python C:\path\to\site_prober.py" /sc daily /st 07:00
```

---

## Email Notifications

Set these environment variables to receive the Excel report by email daily:

```bash
SUPERMU_EMAIL=tu@gmail.com
SUPERMU_PASSWORD=tu_app_password
SUPERMU_RECIPIENT=destinatario@email.com
```
