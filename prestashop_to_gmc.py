import requests
import re
import time
import logging
import unicodedata
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ===================================================
# 1. KONFIGURACJA / CONFIGURATION
# ===================================================
# Uzupełnij poniższe dane przed pierwszym uruchomieniem.
# Fill in the values below before first run.

MERCHANT_ID = 'TWOJE_MERCHANT_ID'          # Google Merchant Center → Ustawienia → Identyfikator konta
PRESTA_KEY  = 'TWOJ_KLUCZ_API_PRESTASHOP'  # PrestaShop → Zaawansowane → Usługi Web
DOMAIN      = 'twojesklep.pl'              # Domena bez "https://" i bez ukośnika na końcu
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Ścieżka do pliku JSON z kluczem serwisowym Google

# Waluta i kraj docelowy
CURRENCY       = 'PLN'   # np. PLN, EUR, USD, GBP
TARGET_COUNTRY = 'PL'    # kod ISO 3166-1 alpha-2, np. PL, DE, FR, GB
LANGUAGE_CODE  = 'pl'    # kod języka produktów w sklepie, np. pl, de, en

# Stawka VAT (jako mnożnik: 1.23 = 23%, 1.19 = 19%, 1.0 = brak VAT)
VAT_MULTIPLIER = 1.23

# Domyślna marka produktów (jeśli sklep nie ma pola brand w PrestaShop)
DEFAULT_BRAND = 'Moja Marka'

# Mapowanie ID kategorii PrestaShop → Google Product Category (numer)
# Lista numerów: https://www.google.com/basepages/producttype/taxonomy-with-ids.pl-PL.txt
# Przykład:
# CATEGORY_MAP = {
#   '12': '436',    # np. PrestaShop "Elektronika" → Google "Elektronika"
#   '15': '2271',   # np. PrestaShop "Odzież" → Google "Odzież > Koszulki"
# }
CATEGORY_MAP = {}
DEFAULT_GOOGLE_CATEGORY = '216'   # Fallback — zmień na kategorię pasującą do Twojego asortymentu


# ===================================================
# 2. LOGOWANIE / LOGGING
# ===================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler('sync.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


# ===================================================
# 3. NARZĘDZIA / HELPERS
# ===================================================

def slugify(value):
    """Zamienia nazwę produktu na przyjazny URL (slug)."""
    if not value:
        return ""
    replacements = {
        'ł': 'l',  'Ł': 'L',
        'ä': 'ae', 'Ä': 'Ae',
        'ö': 'oe', 'Ö': 'Oe',
        'ü': 'ue', 'Ü': 'Ue',
        'ß': 'ss',
        'æ': 'ae', 'Æ': 'Ae',
        'œ': 'oe', 'Œ': 'Oe',
    }
    for char, replacement in replacements.items():
        value = value.replace(char, replacement)
    value = unicodedata.normalize('NFKD', value)
    value = value.encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '-', value)


def clean_html(text):
    """Usuwa tagi HTML i encje HTML z tekstu."""
    if not text:
        return ""
    clean = re.compile('<.*?>|&[a-z0-9]+;')
    return re.sub(clean, '', str(text)).strip()


def get_val(field):
    """Bezpiecznie wyciąga wartość tekstową z pól językowych PrestaShop."""
    if isinstance(field, list) and len(field) > 0:
        return field[0].get('value', '')
    if isinstance(field, dict):
        return field.get('value', '')
    return str(field) if field is not None else ''


# ===================================================
# 4. POBIERANIE PRODUKTÓW / FETCHING PRODUCTS
# ===================================================

def fetch_product_ids_from_category(cat_id):
    """Pobiera ID produktów przypisanych do danej kategorii."""
    url = (
        f'https://{DOMAIN}/api/categories/{cat_id}'
        f'?output_format=JSON&ws_key={PRESTA_KEY}'
    )
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json().get('category', {})
        products = data.get('associations', {}).get('products', [])
        ids = [str(p['id']) for p in products if 'id' in p]
        log.info(f"Kategoria {cat_id}: znaleziono {len(ids)} produktów.")
        return ids
    except Exception as e:
        log.error(f"Błąd pobierania kategorii {cat_id}: {e}")
        return []


def fetch_all_product_ids():
    """Pobiera ID wszystkich produktów ze sklepu (stronicowanie)."""
    all_ids = []
    limit = 50
    offset = 0
    log.info("Pobieram listę wszystkich ID produktów...")
    while True:
        url = (
            f'https://{DOMAIN}/api/products'
            f'?output_format=JSON&display=[id]'
            f'&limit={limit}&start={offset}'
            f'&ws_key={PRESTA_KEY}'
        )
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            batch = response.json().get('products', [])
        except Exception as e:
            log.error(f"Błąd pobierania ID (offset={offset}): {e}")
            break
        if not batch:
            break
        all_ids.extend([str(p['id']) for p in batch])
        if len(batch) < limit:
            break
        offset += limit
    log.info(f"Łącznie produktów w sklepie: {len(all_ids)}")
    return all_ids


def fetch_products_by_ids(product_ids):
    """Pobiera pełne dane produktów po liście ID (partiami po 50)."""
    all_products = []
    batch_size = 50
    log.info(f"Pobieram dane {len(product_ids)} produktów...")
    for i in range(0, len(product_ids), batch_size):
        batch_ids = product_ids[i:i + batch_size]
        id_filter = '|'.join(batch_ids)
        url = (
            f'https://{DOMAIN}/api/products'
            f'?output_format=JSON&display=full'
            f'&filter[id]=[{id_filter}]'
            f'&limit={batch_size}'
            f'&ws_key={PRESTA_KEY}'
        )
        try:
            response = requests.get(url, timeout=120)
            response.raise_for_status()
            batch = response.json().get('products', [])
            all_products.extend(batch)
            log.info(f"  Pobrano {len(all_products)}/{len(product_ids)} produktów...")
        except Exception as e:
            log.error(f"Błąd pobierania partii (batch {i//batch_size + 1}): {e}")
    log.info(f"Pobrano łącznie: {len(all_products)} produktów.")
    return all_products


# ===================================================
# 5. INTERFEJS UŻYTKOWNIKA / USER INTERFACE
# ===================================================

print("\n" + "=" * 54)
print("     🛒  PrestaShop → Google Merchant Center Sync     ")
print("=" * 54)

# --- Wybór kategorii ---
print("\n📂 Pobieram listę kategorii ze sklepu...")
try:
    cat_url = (
        f'https://{DOMAIN}/api/categories'
        f'?output_format=JSON&display=[id,name]&ws_key={PRESTA_KEY}'
    )
    cat_res = requests.get(cat_url, timeout=30)
    cat_res.raise_for_status()
    categories = cat_res.json().get('categories', [])
    print(f"\n{'ID':<6} | NAZWA KATEGORII")
    print("-" * 40)
    for cat in categories:
        print(f"{cat['id']:<6} | {get_val(cat['name'])}")
except Exception as e:
    log.warning(f"Nie udało się wyświetlić listy kategorii: {e}")

print("\n" + "-" * 40)
chosen_cat = input(
    "👉 Wpisz ID kategorii do wysłania (Enter = WSZYSTKIE): "
).strip()

# --- Tryb wysyłki ---
print("\n📋 Wybierz tryb wysyłki:")
print("  [1] Pełna wysyłka      — wyślij wszystkie produkty (insert/nadpisanie)")
print("  [2] Tylko nowe         — pomiń produkty już istniejące w GMC")
print("  [3] Tylko aktualizacja — wyślij wyłącznie produkty już obecne w GMC")
mode_input = input("👉 Wybierz tryb [1/2/3] (Enter = 1): ").strip()
mode = mode_input if mode_input in ('1', '2', '3') else '1'
MODE_LABELS = {
    '1': 'Pełna wysyłka',
    '2': 'Tylko nowe produkty',
    '3': 'Tylko aktualizacja istniejących',
}
log.info(f"Wybrany tryb: {MODE_LABELS[mode]}")


# ===================================================
# 6. POŁĄCZENIE Z GOOGLE / GOOGLE AUTH
# ===================================================

log.info("Łączę się z Google Merchant Center...")
try:
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=['https://www.googleapis.com/auth/content']
    )
    service = build('content', 'v2.1', credentials=credentials)
    log.info("Autoryzacja Google zakończona sukcesem.")
except Exception as e:
    log.error(f"Błąd autoryzacji Google: {e}")
    exit(1)

# Przy trybie 2 lub 3 — pobierz listę produktów już obecnych w GMC
existing_offer_ids = set()
if mode in ('2', '3'):
    log.info("Pobieram listę produktów z GMC...")
    try:
        page_token = None
        while True:
            kwargs = {'merchantId': MERCHANT_ID, 'maxResults': 250}
            if page_token:
                kwargs['pageToken'] = page_token
            result = service.products().list(**kwargs).execute()
            for item in result.get('resources', []):
                raw_id = item.get('id', '')
                offer_id_gmc = raw_id.split(':')[-1] if ':' in raw_id else item.get('offerId', '')
                existing_offer_ids.add(offer_id_gmc)
            page_token = result.get('nextPageToken')
            if not page_token:
                break
        log.info(f"Znaleziono {len(existing_offer_ids)} produktów w GMC.")
    except Exception as e:
        log.error(f"Błąd pobierania listy GMC: {e}")
        exit(1)


# ===================================================
# 7. POBIERANIE PRODUKTÓW Z PRESTASHOP
# ===================================================

if chosen_cat:
    product_ids = fetch_product_ids_from_category(chosen_cat)
else:
    product_ids = fetch_all_product_ids()

if not product_ids:
    log.error("Brak produktów do wysłania. Sprawdź konfigurację.")
    exit(1)

products = fetch_products_by_ids(product_ids)

if not products:
    log.error("Nie udało się pobrać danych produktów. Sprawdź klucz API i domenę.")
    exit(1)


# ===================================================
# 8. PĘTLA WYSYŁKI / SYNC LOOP
# ===================================================

success_count  = 0
skip_count     = 0
skip_inactive  = 0
error_count    = 0

log.info("Rozpoczynam synchronizację produktów...")

for p in products:
    p_id = str(p.get('id', ''))
    try:
        # Pomiń produkty nieaktywne
        if str(p.get('active', '1')) == '0':
            log.info(f"   [~] Pominięto ID {p_id}: produkt nieaktywny.")
            skip_inactive += 1
            continue

        # Dane podstawowe
        name      = get_val(p.get('name'))
        reference = p.get('reference', '').strip()
        offer_id  = reference if reference else p_id

        # Filtr trybu wysyłki
        if mode == '2' and offer_id in existing_offer_ids:
            log.info(f"   [~] Pominięto {offer_id}: już istnieje w GMC.")
            skip_count += 1
            continue
        if mode == '3' and offer_id not in existing_offer_ids:
            log.info(f"   [~] Pominięto {offer_id}: brak w GMC (tryb aktualizacji).")
            skip_count += 1
            continue

        # Weryfikacja zdjęcia
        img_id = p.get('id_default_image')
        if not img_id or str(img_id).strip() in ('0', ''):
            log.warning(f"   [!] Pominięto ID {p_id}: brak zdjęcia głównego.")
            skip_count += 1
            continue

        # URL produktu i zdjęcia
        link_name   = slugify(name)
        product_url = f"https://{DOMAIN}/{p_id}-{link_name}.html"
        img_path    = '/'.join(str(img_id))
        image_url   = f"https://{DOMAIN}/img/p/{img_path}/{img_id}-large_default.jpg"

        # Cena brutto
        price_brutto = round(float(p.get('price') or 0) * VAT_MULTIPLIER, 2)

        # Kategoria Google
        cat_id         = str(p.get('id_category_default', ''))
        google_category = CATEGORY_MAP.get(cat_id, DEFAULT_GOOGLE_CATEGORY)

        # Waga (PrestaShop: kg → g)
        weight_raw = float(p.get('weight') or 0) * 1000
        weight     = int(weight_raw) if weight_raw > 0 else 500

        # Opis
        description = (
            clean_html(get_val(p.get('description_short')))[:4900]
            or clean_html(get_val(p.get('description')))[:4900]
            or name
        )

        # Paczka danych dla Google Content API
        item = {
            'offerId':             offer_id,
            'title':               name[:150],
            'description':         description,
            'link':                product_url,
            'imageLink':           image_url,
            'contentLanguage':     LANGUAGE_CODE,
            'targetCountry':       TARGET_COUNTRY,
            'channel':             'online',
            'availability':        'in stock',
            'condition':           'new',
            'price':               {'value': str(price_brutto), 'currency': CURRENCY},
            'brand':               DEFAULT_BRAND,
            'mpn':                 offer_id,
            'googleProductCategory': google_category,
            'shippingWeight':      {'value': str(weight), 'unit': 'g'},
        }

        service.products().insert(merchantId=MERCHANT_ID, body=item).execute()
        log.info(f"   [OK] {offer_id} | {name[:50]}...")
        success_count += 1

        # Przerwa — ochrona przed limitem Google API (~1 req/s)
        time.sleep(0.5)

    except Exception as e:
        log.error(f"   [X] Błąd przy ID {p_id}: {e}")
        error_count += 1


# ===================================================
# 9. PODSUMOWANIE / SUMMARY
# ===================================================

print("\n" + "=" * 54)
print("🏁  SYNCHRONIZACJA ZAKOŃCZONA!")
print(f"✅  Wysłano poprawnie:                {success_count}")
print(f"🟡  Pominięto (filtr trybu / zdjęcia): {skip_count}")
print(f"⚫  Pominięto (nieaktywne):            {skip_inactive}")
print(f"🔴  Błędy techniczne:                 {error_count}")
print(f"📄  Szczegóły w pliku:                sync.log")
print("=" * 54)
