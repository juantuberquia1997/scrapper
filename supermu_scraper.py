import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import time
import random
import urllib.parse
# --- CONFIGURATION ---
# User agent to mimic a real browser to avoid being blocked
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
# EMAIL CONFIGURATION (Fill these in to enable email)
ENABLE_EMAIL = False  # Set to True after configuring credentials
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"  # Use App Password if 2FA is on
RECIPIENT_EMAIL = "recipient_email@example.com"
# Product list based on user request
PRODUCTS_TO_TRACK = [
  "CEBOLLA ROJA",
  "PAPA CRIOLLA",
  "GRANADILLA BOLSA EC",
  "PAPA GRUESA 1U",
  "MARACUYA",
  "PLATANO VERDE",
  "PAQUETE FRUVER LIMO",
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
  "JABON PROTEX 3U 330",
  "CERA PARA PEINAR EG",
  "AMBIENT GLADE 400ML",
  "PAPEL ALUMINIO ZEUX",
  "CREMA COLGATE 3U 75",
  "JABON BARRA DERSA 3",
  "ESPONJA ORO PLATA B"
]
def check_product(product_name):
    """
    Searches for a product on Supermu and returns info if found.
    """
    print(f"Searching for: {product_name}...")
    
    encoded_name = urllib.parse.quote(product_name)
    url = f"https://supermu.com/search?q={encoded_name}"
    
    headers = {'User-Agent': USER_AGENT}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Based on research, products are in 'product-item' or search results grid
        # We look for the first product-item in the grid
        
        # Selector identified in research:
        # Title: .product-collection__title a
        # Price: .price
        # Sale Badge: .label.label--sale (or check if it exists/visible)
        
        product_item = soup.select_one('product-item')
        
        if not product_item:
            print(f"  -> [!] No products found for '{product_name}'")
            return None
            
        title_elem = product_item.select_one('.product-collection__title a')
        price_elem = product_item.select_one('.price')
        sale_label = product_item.select_one('.label--sale')
        
        if not title_elem or not price_elem:
            print(f"  -> [!] Incomplete data for '{product_name}'")
            return None
            
        title = title_elem.get_text(strip=True)
        # Search result price (might not be the discounted one if it's a daily deal hidden inside)
        price = price_elem.get_text(strip=True)
        link = "https://supermu.com" + title_elem['href']
        
        is_discounted = False
        discount_info = ""
        
        # --- Deep Scrape: Visit Product Page ---
        # User reported some discounts (daily-discount-tag) are only visible or structured this way
        print(f"  -> Checking detail page: {link}")
        time.sleep(random.uniform(0.5, 1.5)) # Polite delay
        
        detail_response = requests.get(link, headers=headers)
        if detail_response.status_code == 200:
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            
            # Check for Daily Discount Tag
            # <div class="daily-discount-tag compact-discount-label">
            #   <span class="discount-percent-label">Ahora -25%</span>
            #   <span class="discount-price-final">$4.950</span>
            # </div>
            
            daily_discount_tag = detail_soup.select_one('.daily-discount-tag')
            
            if daily_discount_tag:
                final_price_elem = daily_discount_tag.select_one('.discount-price-final')
                percent_elem = daily_discount_tag.select_one('.discount-percent-label')
                
                if final_price_elem:
                    is_discounted = True
                    price = final_price_elem.get_text(strip=True) # Update price to the real final price
                    percent_text = percent_elem.get_text(strip=True) if percent_elem else "Deal"
                    discount_info = f"{percent_text} (Daily Deal)"
            else:
                # Fallback to standard badge if daily tag not found
                # Method 1: Check for sale label on detail page or previous search result
                sale_label = detail_soup.select_one('.label--sale')
                if sale_label and sale_label.get_text(strip=True):
                     is_discounted = True
                     discount_info = f"Badge: {sale_label.get_text(strip=True)}"
        else:
            print("  -> [!] Failed to fetch detail page, using search result data.")
            # Fallback to search result data
            sale_label = product_item.select_one('.label--sale')
            if sale_label and sale_label.get_text(strip=True):
                 is_discounted = True
                 discount_info = f"Badge: {sale_label.get_text(strip=True)}"
             
        found_data = {
            "search_term": product_name,
            "title": title,
            "price": price,
            "link": link,
            "is_discounted": is_discounted,
            "discount_info": discount_info
        }
        
        status_msg = " [DISCOUNT!]" if is_discounted else ""
        print(f"  -> Found: {title} | {price}{status_msg}")
        return found_data
    except Exception as e:
        print(f"  -> Error searching {product_name}: {e}")
        return None
def send_email(discounted_products, all_products_found):
    if not ENABLE_EMAIL:
        print("\n--- Email Sending Disabled (ENABLE_EMAIL = False) ---")
        print("Set ENABLE_EMAIL=True and configure credentials to send emails.")
        return
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECIPIENT_EMAIL
    
    count_discounts = len(discounted_products)
    msg['Subject'] = f"Supermu Scraper Report: {count_discounts} Discounts Found"
    body = f"<h2>Supermu Price Report</h2>"
    body += f"<p>Checked {len(PRODUCTS_TO_TRACK)} items. Found {len(all_products_found)} items in stock.</p>"
    
    if discounted_products:
        body += "<h3>🔥 Discounted Items 🔥</h3><ul>"
        for p in discounted_products:
            body += f"<li><b>{p['title']}</b>: {p['price']} <a href='{p['link']}'>Link</a></li>"
        body += "</ul>"
    else:
        body += "<p>No specific discounts detected based on 'Sale' labels.</p>"
        
    if all_products_found:
        body += "<h3>All Found Items</h3><ul>"
        for p in all_products_found:
             extra = " (DISCOUNT)" if p['is_discounted'] else ""
             body += f"<li>{p['title']}: {p['price']}{extra}</li>"
        body += "</ul>"
    msg.attach(MIMEText(body, 'html'))
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
def main():
    print("Starting Supermu Scraper...")
    
    discounted_items = []
    all_found_items = []
    
    # We will check a subset for testing if list is too long, but user asked for all.
    # To be polite to the server, we add a delay.
    
    for product in PRODUCTS_TO_TRACK:
        data = check_product(product)
        if data:
            all_found_items.append(data)
            if data['is_discounted']:
                discounted_items.append(data)
        
        # Random delay to behave like a human
        time.sleep(random.uniform(1, 3))
        
    print("\n" + "="*30)
    print("SUMMARY")
    print("="*30)
    print(f"Total Searched: {len(PRODUCTS_TO_TRACK)}")
    print(f"Found: {len(all_found_items)}")
    print(f"Discounts: {len(discounted_items)}")
    
    if discounted_items:
        print("\nDiscounted Items:")
        for item in discounted_items:
            print(f"- {item['title']}: {item['price']} ({item['link']})")
            
    send_email(discounted_items, all_found_items)
if __name__ == "__main__":
    main()
