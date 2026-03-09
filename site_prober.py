"""
Supermu Discount Tracker
Searches each product in PRODUCTS_TO_TRACK and reports which ones
have active discounts or promotions.
"""
import re
import time
import random
import urllib.parse

import requests
from bs4 import BeautifulSoup
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

from supermu_scraper import PRODUCTS_TO_TRACK

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://supermu.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/91.0.4472.124 Safari/537.36"
    )
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_price(text: str) -> float | None:
    """Colombian format: '.' = thousands sep, ',' = decimal sep."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text)
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    else:
        cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned) if cleaned else None
    except ValueError:
        return None


def fmt_cop(value: float | None) -> str:
    return f"${value:,.0f}" if value is not None else ""


# ---------------------------------------------------------------------------
# Search & parse
# ---------------------------------------------------------------------------

def search_product(term: str) -> dict:
    """
    Search supermu.com for `term` and return the first result with
    full discount info. Returns a result dict regardless of whether
    the product or discount was found.
    """
    result = {
        "search_term": term,
        "title": "",
        "url": "",
        "found": False,
        "has_discount": False,
        "original_price": None,
        "discounted_price": None,
        "savings_cop": None,
        "savings_pct": None,
        "discount_label": "",
    }

    encoded = urllib.parse.quote(term)
    search_url = f"{BASE_URL}/search?q={encoded}"

    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  [ERROR] {term}: {e}")
        return result

    soup = BeautifulSoup(resp.text, "html.parser")
    item = soup.select_one("product-item")

    if not item:
        print(f"  [NOT FOUND] {term}")
        return result

    # Title & URL
    acciones = item.find("div", class_="acciones")
    if acciones:
        result["title"] = acciones.get("data-product-title", "").strip()
        path = acciones.get("data-product-url", "").split("?")[0]
        result["url"] = BASE_URL + path if path else ""
    else:
        h4 = item.find("h4")
        result["title"] = h4.get_text(strip=True) if h4 else term

    result["found"] = True

    # Discount block
    discount_tag = item.select_one(".daily-discount-tag")
    if discount_tag:
        original_el = discount_tag.select_one(".discount-price-original")
        final_el    = discount_tag.select_one(".discount-price-final")
        label_el    = discount_tag.select_one(".discount-percent-label")

        orig  = parse_price(original_el.get_text()) if original_el else None
        final = parse_price(final_el.get_text())    if final_el    else None
        label = label_el.get_text(strip=True)       if label_el    else ""

        result["has_discount"]     = True
        result["original_price"]   = orig
        result["discounted_price"] = final
        result["discount_label"]   = label

        if orig and final:
            result["savings_cop"] = orig - final
            result["savings_pct"] = round((orig - final) / orig * 100, 1)
    else:
        # Fallback: check for a sale label badge
        sale = item.select_one(".label--sale")
        if sale and sale.get_text(strip=True):
            result["has_discount"]   = True
            result["discount_label"] = sale.get_text(strip=True)

        # Grab listed price even without discount
        price_el = item.select_one("span[data-js-product-price] span")
        if price_el:
            result["original_price"] = parse_price(price_el.get_text())

    status = f"DESCUENTO: {result['discount_label']}" if result["has_discount"] else "sin descuento"
    print(f"  {result['title'][:50]:<50} {status}")
    return result


# ---------------------------------------------------------------------------
# Excel export
# ---------------------------------------------------------------------------

# Palette
C_GREEN_DARK  = "1F5C2E"
C_GREEN_MID   = "2E7D32"
C_GREEN_LIGHT = "E8F5E9"
C_ORANGE      = "E65100"
C_YELLOW      = "FFF9C4"
C_WHITE       = "FFFFFF"
C_GRAY        = "F5F5F5"
C_RED_LIGHT   = "FFEBEE"


def _hcell(ws, row, col, value, bg=C_GREEN_DARK, fg=C_WHITE, size=11):
    cell = ws.cell(row=row, column=col, value=value)
    cell.fill = PatternFill("solid", fgColor=bg)
    cell.font = Font(bold=True, color=fg, size=size)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    return cell


def _col_widths(ws, widths: list[int]):
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w


def export_excel(results: list[dict], filename: str) -> None:
    wb = openpyxl.Workbook()

    discounted = [r for r in results if r["has_discount"]]
    not_found  = [r for r in results if not r["found"]]
    found_no_discount = [r for r in results if r["found"] and not r["has_discount"]]

    # ── Sheet 1: Products WITH discount (sorted by savings%) ────────────────
    ws1 = wb.active
    ws1.title = "Con Descuento"

    h1 = ["Termino Buscado", "Producto Encontrado", "Precio Original (COP)",
          "Precio con Descuento (COP)", "Ahorro (COP)", "Ahorro (%)",
          "Etiqueta Promocion", "URL"]
    w1 = [28, 50, 24, 26, 18, 12, 22, 65]

    for c, h in enumerate(h1, 1):
        _hcell(ws1, 1, c, h)
    _col_widths(ws1, w1)
    ws1.row_dimensions[1].height = 30
    ws1.freeze_panes = "A2"

    sorted_disc = sorted(discounted, key=lambda x: x["savings_pct"] or 0, reverse=True)
    for ri, r in enumerate(sorted_disc, start=2):
        bg = C_GREEN_LIGHT if ri % 2 == 0 else C_WHITE
        row = [
            r["search_term"], r["title"],
            r["original_price"], r["discounted_price"],
            r["savings_cop"], r["savings_pct"],
            r["discount_label"], r["url"],
        ]
        for ci, val in enumerate(row, start=1):
            cell = ws1.cell(row=ri, column=ci, value=val)
            cell.fill = PatternFill("solid", fgColor=bg)
            cell.alignment = Alignment(vertical="center")
            if ci in (3, 4, 5) and isinstance(val, (int, float)):
                cell.number_format = '"$"#,##0'
            if ci == 6 and isinstance(val, (int, float)):
                cell.number_format = '0.0"%"'
                if val >= 20:
                    cell.font = Font(bold=True, color=C_ORANGE)

    # ── Sheet 2: Full results (all products) ────────────────────────────────
    ws2 = wb.create_sheet("Todos los Resultados")

    h2 = ["#", "Termino Buscado", "Producto Encontrado", "Estado",
          "Precio Original (COP)", "Precio Desc. (COP)", "Ahorro (%)",
          "Etiqueta Promocion", "URL"]
    w2 = [5, 28, 50, 18, 24, 24, 12, 22, 65]

    for c, h in enumerate(h2, 1):
        _hcell(ws2, 1, c, h)
    _col_widths(ws2, w2)
    ws2.row_dimensions[1].height = 30
    ws2.freeze_panes = "B2"

    for ri, r in enumerate(results, start=2):
        if not r["found"]:
            status, bg = "No encontrado", C_RED_LIGHT
        elif r["has_discount"]:
            status, bg = "DESCUENTO", C_YELLOW
        else:
            status, bg = "Sin descuento", C_WHITE if ri % 2 == 0 else C_GRAY

        row = [
            ri - 1, r["search_term"], r["title"], status,
            r["original_price"], r["discounted_price"],
            r["savings_pct"], r["discount_label"], r["url"],
        ]
        for ci, val in enumerate(row, start=1):
            cell = ws2.cell(row=ri, column=ci, value=val)
            cell.fill = PatternFill("solid", fgColor=bg)
            cell.alignment = Alignment(vertical="center")
            if ci in (5, 6) and isinstance(val, (int, float)):
                cell.number_format = '"$"#,##0'
            if ci == 7 and isinstance(val, (int, float)):
                cell.number_format = '0.0"%"'
            if status == "DESCUENTO" and ci == 4:
                cell.font = Font(bold=True, color=C_ORANGE)

    # ── Sheet 3: Summary ────────────────────────────────────────────────────
    ws3 = wb.create_sheet("Resumen")
    summary_data = [
        ("Total productos buscados",    len(results)),
        ("Encontrados",                 len(results) - len(not_found)),
        ("No encontrados",              len(not_found)),
        ("Con descuento / promocion",   len(discounted)),
        ("Sin descuento",               len(found_no_discount)),
        ("", ""),
        ("Fecha del reporte",           datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]

    _hcell(ws3, 1, 1, "Indicador", bg=C_GREEN_DARK)
    _hcell(ws3, 1, 2, "Valor",     bg=C_GREEN_DARK)
    ws3.column_dimensions["A"].width = 35
    ws3.column_dimensions["B"].width = 20

    for ri, (label, value) in enumerate(summary_data, start=2):
        ws3.cell(row=ri, column=1, value=label).font = Font(bold=bool(label))
        ws3.cell(row=ri, column=2, value=value)

    # Highlight the discount count row
    disc_row = 6  # row index for "Con descuento" (starts at 2 + offset 3 = row 6 if 0-indexed correctly)
    # Actually: row 2=total, 3=found, 4=not found, 5=with discount
    ws3.cell(row=5, column=1).font = Font(bold=True, color=C_ORANGE)
    ws3.cell(row=5, column=2).font = Font(bold=True, color=C_ORANGE)

    wb.save(filename)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    total = len(PRODUCTS_TO_TRACK)
    print(f"Supermu Discount Tracker")
    print(f"Buscando {total} productos...\n")

    results = []
    for i, term in enumerate(PRODUCTS_TO_TRACK, start=1):
        print(f"[{i:>2}/{total}] {term}")
        result = search_product(term)
        results.append(result)
        time.sleep(random.uniform(0.8, 1.5))

    discounted = [r for r in results if r["has_discount"]]
    not_found  = [r for r in results if not r["found"]]

    print(f"\n{'='*55}")
    print(f"  RESUMEN")
    print(f"{'='*55}")
    print(f"  Buscados:          {total}")
    print(f"  Encontrados:       {total - len(not_found)}")
    print(f"  No encontrados:    {len(not_found)}")
    print(f"  Con descuento:     {len(discounted)}")

    if discounted:
        print(f"\n  --- Productos con descuento ---")
        top = sorted(discounted, key=lambda x: x["savings_pct"] or 0, reverse=True)
        for r in top:
            savings = f"  Ahorro: {r['savings_pct']}%" if r["savings_pct"] else ""
            print(f"  {r['title'][:50]:<50} {r['discount_label']}{savings}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"supermu_descuentos_{timestamp}.xlsx"
    export_excel(results, filename)
    print(f"\n  Reporte guardado: {filename}")


if __name__ == "__main__":
    main()
