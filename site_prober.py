"""
Supermu Discount Tracker
Searches each product in PRODUCTS_TO_TRACK, exports an Excel report,
and sends it by email.
"""
import re
import time
import random
import urllib.parse
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import requests
from bs4 import BeautifulSoup
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

# ---------------------------------------------------------------------------
# Email config  ← fill these in before enabling
# ---------------------------------------------------------------------------
ENABLE_EMAIL    = bool(os.getenv("SUPERMU_EMAIL"))
SMTP_SERVER     = "smtp.gmail.com"
SMTP_PORT       = 587
SENDER_EMAIL    = os.getenv("SUPERMU_EMAIL", "")
SENDER_PASSWORD = os.getenv("SUPERMU_PASSWORD", "")
RECIPIENT_EMAIL = os.getenv("SUPERMU_RECIPIENT", "")

# ---------------------------------------------------------------------------
# Products to track
# ---------------------------------------------------------------------------
PRODUCTS_TO_TRACK = [
    "CEBOLLA ROJA",
    "PAPA CRIOLLA",
    "GRANADILLA",
    "PAPA CAPIRA",
    "MARACUYA",
    "PLATANO VERDE",
    "LIMON TAHITI",
    "TOMATE DE ARBOL",
    "AGUACATE PAPELILLO",
    "GUINEO",
    "MORA",
    "FRIJOL VERDE DESGRA",
    "BANANO CRIOLLO",
    "TOMATE CHONTO",
    "FRESA JUMBO BANDEJA",
    "ARVEJA ZENU 2U 600G",
    "EMPANADA MAFRY 760G",
    "ACEITE CADA DIA 300",
    "AREPA SUPERMU 15U 1",
    "PANELA SAN JOAQUIN",
    "ESPARCIBLE CAMPI 50",
    "ACEITUNAS VERDES SE",
    "HARINA TRIGO HAZ OR",
    "ARROZ DIANA 1000 G",
    "ARROZ DIANA 2500G P",
    "ATUN VANCAMPS 160G",
    "AZUCAR PROVIDENCIA",
    "PASTA DORIA 250G CA",
    "PASTA DORIA 250G CO",
    "SAL REFISAL 1000G",
    "HARINA MAIZ PAN 100",
    "CHOCOLATE TESALIA 2",
    "CALDO DONA GALLINA",
    "MANI DULCE LA VAQUI",
    "LENTEJA ABURRA 500G",
    "CHOCOLATES M&M 47.9",
    "CALDO RICOSTILLA 12",
    "LECHE LA VAQUITA 6U",
    "CERVEZA AGUILA 6U 1",
    "SAL DE AJO BORNEO 1",
    "SALSA MEXICAN ESTIL",
    "GALLETA DUCALES NOE",
    "GALLETA WAFER NOEL",
    "GALLETA COCOSETTE",
    "GALLETA BRIDGE 151G",
    "GALLETA CLUB SOCIAL",
    "GALLETA SALTIN NOEL",
    "CHOC JUMBO MANI 10U",
    "TOSTADA MAMA INES 2",
    "MINICROISSANT LA VA",
    "PAN BALLENA NATIPAN",
    "AROMATICA JAIBEL 20",
    "PAN TAJADO LA VAQUI",
    "BOLSA VAQUITA ECOLO",
    "ROSQUILLAS SEBA SEB",
    "LONCHERA DIVERTIDA",
    "SERVILLETA FAVORITA",
    "PLATO DESECHABLE KI",
    "LOZACREAM LIQ BLANC",
    "DETERG LIQ FANZ 200",
    "TOALLA COCINA FAMIL",
    "ENJUA COLGATE 500ML",
    "SUAVIZANTE FANZ 200",
    "VINAGRE BLANCO LA V",
    "JABON PROTEX 3U 330",
    "CERA PARA PEINAR EG",
    "AMBIENT GLADE 400ML",
    "PAPEL ALUMINIO ZEUX",
    "CREMA COLGATE 3U 75",
    "JABON BARRA DERSA 3",
    "ESPONJA ORO PLATA B",
]

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
    discount_tag = item.select_one(".daily-discount-tag, .collection-discount-tag")
    if discount_tag:
        original_el = discount_tag.select_one(".discount-price-original")
        final_el    = discount_tag.select_one(".discount-price-final")
        label_el    = discount_tag.select_one(".discount-percent-label")

        orig  = parse_price(original_el.get_text()) if original_el else None
        final = parse_price(final_el.get_text())    if final_el    else None
        label = label_el.get_text(strip=True)       if label_el    else ""

        # Si no hay precio original en el tag, tomarlo del precio listado
        if orig is None:
            price_el = item.select_one("span[data-js-product-price] span")
            if price_el:
                orig = parse_price(price_el.get_text())

        # Si no hay precio final, calcularlo desde el porcentaje del label
        if final is None and orig and label:
            pct_match = re.search(r"(\d+)", label)
            if pct_match:
                pct = float(pct_match.group(1))
                final = round(orig * (1 - pct / 100))

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

    discounted        = [r for r in results if r["has_discount"]]
    not_found         = [r for r in results if not r["found"]]
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
        ("Total productos buscados",  len(results)),
        ("Encontrados",               len(results) - len(not_found)),
        ("No encontrados",            len(not_found)),
        ("Con descuento / promocion", len(discounted)),
        ("Sin descuento",             len(found_no_discount)),
        ("", ""),
        ("Fecha del reporte",         datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]

    _hcell(ws3, 1, 1, "Indicador", bg=C_GREEN_DARK)
    _hcell(ws3, 1, 2, "Valor",     bg=C_GREEN_DARK)
    ws3.column_dimensions["A"].width = 35
    ws3.column_dimensions["B"].width = 20

    for ri, (label, value) in enumerate(summary_data, start=2):
        ws3.cell(row=ri, column=1, value=label).font = Font(bold=bool(label))
        ws3.cell(row=ri, column=2, value=value)

    ws3.cell(row=5, column=1).font = Font(bold=True, color=C_ORANGE)
    ws3.cell(row=5, column=2).font = Font(bold=True, color=C_ORANGE)

    wb.save(filename)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

def send_email(filename: str, discounted: list[dict], total: int) -> None:
    if not ENABLE_EMAIL:
        print("\n--- Email desactivado (ENABLE_EMAIL = False) ---")
        return

    msg = MIMEMultipart()
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg["Subject"] = (
        f"Supermu Reporte {datetime.now().strftime('%Y-%m-%d')} "
        f"— {len(discounted)} descuento(s) encontrado(s)"
    )

    body_lines = [
        f"<h2>Supermu — Reporte diario de descuentos</h2>",
        f"<p>Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>",
        f"<p>Productos buscados: <b>{total}</b> | Con descuento: <b>{len(discounted)}</b></p>",
    ]

    if discounted:
        top = sorted(discounted, key=lambda x: x["savings_pct"] or 0, reverse=True)
        body_lines.append("<h3>Productos con descuento (mayor a menor ahorro)</h3><ul>")
        for r in top:
            savings = f" — Ahorro: {r['savings_pct']}%" if r["savings_pct"] else ""
            link    = f" <a href='{r['url']}'>Ver</a>" if r["url"] else ""
            body_lines.append(
                f"<li><b>{r['title']}</b>: {fmt_cop(r['discounted_price'])} "
                f"(antes {fmt_cop(r['original_price'])}){savings}{link}</li>"
            )
        body_lines.append("</ul>")
    else:
        body_lines.append("<p>No se detectaron descuentos hoy.</p>")

    body_lines.append("<p><i>Reporte completo adjunto en Excel.</i></p>")
    msg.attach(MIMEText("\n".join(body_lines), "html"))

    # Attach Excel file
    with open(filename, "rb") as f:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(f.read())
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{os.path.basename(filename)}"')
    msg.attach(part)

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        print(f"  Email enviado a {RECIPIENT_EMAIL}")
    except Exception as e:
        print(f"  [ERROR] No se pudo enviar el email: {e}")


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
    filename  = f"supermu_descuentos_{timestamp}.xlsx"
    export_excel(results, filename)
    print(f"\n  Reporte guardado: {filename}")

    send_email(filename, discounted, total)


if __name__ == "__main__":
    main()
