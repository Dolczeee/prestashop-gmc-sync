# 🛒 PrestaShop → Google Merchant Center Sync

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![PrestaShop](https://img.shields.io/badge/PrestaShop-1.7%20%2F%208.x-DF0067?logo=prestashop&logoColor=white)
![Google Shopping](https://img.shields.io/badge/Google%20Merchant%20Center-Content%20API%20v2.1-4285F4?logo=google&logoColor=white)
![Maintenance](https://img.shields.io/badge/Maintained-yes-brightgreen)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

Skrypt Python do automatycznej synchronizacji produktów z PrestaShop do Google Merchant Center (Google Shopping).

> Działa z PrestaShop 1.7 / 8.x i Google Content API v2.1.  
> Nie wymaga żadnych płatnych narzędzi ani wtyczek.

🇬🇧 [English version → README.md](README.md)

---

## 📋 Spis treści

- [Wymagania](#-wymagania)
- [Instalacja](#-instalacja)
- [Krok 1 — Klucz API PrestaShop](#krok-1--klucz-api-prestashop)
- [Krok 2 — Konto usługi Google (Service Account)](#krok-2--konto-usługi-google-service-account)
- [Krok 3 — Merchant ID](#krok-3--merchant-id)
- [Krok 4 — Konfiguracja skryptu](#krok-4--konfiguracja-skryptu)
- [Uruchamianie](#-uruchamianie)
- [Tryby wysyłki](#-tryby-wysyłki)
- [Mapowanie kategorii](#-mapowanie-kategorii)
- [Rozwiązywanie problemów](#-rozwiązywanie-problemów)

---

## ✅ Wymagania

- Python **3.8+**
- Dostęp do panelu administracyjnego PrestaShop
- Konto Google Merchant Center
- Projekt w Google Cloud Console

---

## 📦 Instalacja

```bash
# Sklonuj repozytorium
git clone https://github.com/TWOJ_LOGIN/prestashop-gmc-sync.git
cd prestashop-gmc-sync

# Zainstaluj zależności
pip install requests google-auth google-api-python-client
```

---

## Krok 1 — Klucz API PrestaShop

Klucz API umożliwia skryptowi odczytywanie produktów z Twojego sklepu.

1. Zaloguj się do **panelu administracyjnego PrestaShop**.
2. Przejdź do: `Zaawansowane` → `Usługi sieciowe` (Web Services).

   > Jeśli nie widzisz tej opcji: `Parametry zaawansowane` → `Usługi sieciowe`.

3. Upewnij się, że usługi sieciowe są **włączone** (przełącznik na górze strony).
4. Kliknij **„Dodaj nowy klucz"** (ikona `+`).
5. Ustaw uprawnienia — skrypt potrzebuje tylko **odczytu (GET)**. Zaznacz `GET` dla:
   - `products`
   - `categories`
   - `images`
6. Dodaj opis, np. `GMC Sync`.
7. Kliknij **Zapisz**.
8. Skopiuj wygenerowany klucz (długi ciąg znaków) — to Twój `PRESTA_KEY`.

> ⚠️ Klucz jest widoczny tylko raz po utworzeniu — zapisz go od razu!

---

## Krok 2 — Konto usługi Google (Service Account)

Skrypt używa uwierzytelniania serwer-serwer, bez potrzeby logowania przez przeglądarkę.

### 2a. Utwórz projekt w Google Cloud Console

1. Wejdź na [console.cloud.google.com](https://console.cloud.google.com).
2. Kliknij **„Wybierz projekt"** → **„Nowy projekt"**.
3. Nadaj mu dowolną nazwę, np. `gmc-sync`.
4. Kliknij **Utwórz**.

### 2b. Włącz Content API for Shopping

1. W menu po lewej: `Interfejsy API i usługi` → `Biblioteka`.
2. Wyszukaj **„Content API for Shopping"**.
3. Kliknij wynik i wybierz **Włącz**.

### 2c. Utwórz konto usługi (Service Account)

1. Przejdź do: `Interfejsy API i usługi` → `Dane logowania`.
2. Kliknij **„Utwórz dane logowania"** → **„Konto usługi"**.
3. Nadaj nazwę, np. `gmc-sync-account`, kliknij **Utwórz i kontynuuj**.
4. W sekcji uprawnień możesz pominąć (kliknij **Kontynuuj** → **Gotowe**).
5. Na liście kont usługi kliknij na nowo utworzone konto.
6. Przejdź do zakładki **Klucze** → **Dodaj klucz** → **Utwórz nowy klucz**.
7. Wybierz format **JSON** → **Utwórz**.
8. Plik `.json` zostanie pobrany automatycznie — **umieść go w folderze ze skryptem** i zaktualizuj zmienną `SERVICE_ACCOUNT_FILE` w `prestashop_to_gmc.py`.

### 2d. Powiąż konto usługi z Merchant Center

1. Skopiuj adres e-mail konta usługi (widoczny w Google Cloud Console, format: `nazwa@projekt.iam.gserviceaccount.com`).
2. Wejdź na [merchants.google.com](https://merchants.google.com).
3. Kliknij ikonę ⚙️ (Ustawienia) → **Dostęp do konta**.
4. Kliknij **„Dodaj użytkownika"**.
5. Wklej e-mail konta usługi, wybierz rolę **Administrator** lub **Standard**.
6. Kliknij **Dodaj użytkownika**.

> ✅ Od tej chwili skrypt ma dostęp do Twojego Merchant Center.

---

## Krok 3 — Merchant ID

1. Zaloguj się do [merchants.google.com](https://merchants.google.com).
2. Twój **Merchant ID** (identyfikator konta) jest widoczny:
   - W prawym górnym rogu obok nazwy sklepu,
   - lub pod `⚙️ Ustawienia` → `Informacje o koncie`.
3. To kilkucyfrowy numer, np. `123456789`.

---

## Krok 4 — Konfiguracja skryptu

Otwórz plik `prestashop_to_gmc.py` i wypełnij sekcję konfiguracyjną na górze:

```python
MERCHANT_ID          = '123456789'          # Twój Merchant ID z Google Merchant Center
PRESTA_KEY           = 'ABCDEF1234567890'   # Klucz API z PrestaShop
DOMAIN               = 'twojesklep.pl'      # Domena bez https:// i bez /
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Nazwa pliku JSON pobranego z Google Cloud

CURRENCY             = 'PLN'   # Waluta: PLN, EUR, USD, GBP...
TARGET_COUNTRY       = 'PL'    # Kraj docelowy (ISO): PL, DE, FR, GB...
LANGUAGE_CODE        = 'pl'    # Język produktów: pl, de, en...

VAT_MULTIPLIER       = 1.23    # Stawka VAT: 1.23 = 23%, 1.19 = 19%, 1.0 = bez VAT

DEFAULT_BRAND        = 'Moja Marka'   # Domyślna marka produktów
DEFAULT_GOOGLE_CATEGORY = '216'       # Domyślna kategoria Google (patrz sekcja niżej)
```

### Struktura katalogu po konfiguracji

```
prestashop-gmc-sync/
├── prestashop_to_gmc.py
├── service_account.json   ← plik pobrany z Google Cloud Console
├── sync.log               ← tworzony automatycznie po pierwszym uruchomieniu
└── README.md
```

> ⚠️ Dodaj `service_account.json` do `.gitignore` — nigdy nie wgrywaj kluczy prywatnych na GitHub!

---

## ▶️ Uruchamianie

```bash
python prestashop_to_gmc.py
```

Skrypt wyświetli listę kategorii z Twojego sklepu, a następnie zapyta:
1. **Które kategorie** chcesz wysłać (lub wszystkie).
2. **Tryb wysyłki** (patrz niżej).

---

## 🔄 Tryby wysyłki

| Tryb | Opis |
|------|------|
| `1` — Pełna wysyłka | Wysyła wszystkie produkty. Istniejące wpisy w GMC są nadpisywane. |
| `2` — Tylko nowe | Pomija produkty, które już istnieją w GMC. Przydatne przy pierwszej migracji fragmentu katalogu. |
| `3` — Tylko aktualizacja | Wysyła wyłącznie produkty, które już są w GMC. Nie dodaje nowych. |

---

## 🗂️ Mapowanie kategorii

Google wymaga przypisania każdego produktu do kategorii z taksonomii Google.  
Możesz zmapować swoje kategorie PrestaShop na numery Google:

```python
CATEGORY_MAP = {
    '12': '436',    # ID kat. PrestaShop → numer kategorii Google
    '15': '2271',
    '8':  '111',
}
```

Pełna lista numerów kategorii Google:  
🔗 [taxonomy-with-ids.pl-PL.txt](https://www.google.com/basepages/producttype/taxonomy-with-ids.pl-PL.txt)

Jeśli kategoria nie jest zmapowana, użyta zostanie wartość `DEFAULT_GOOGLE_CATEGORY`.

---

## 🔍 Rozwiązywanie problemów

| Problem | Prawdopodobna przyczyna | Rozwiązanie |
|---------|------------------------|-------------|
| `403 Forbidden` przy PrestaShop | Klucz API bez uprawnień GET | Sprawdź uprawnienia klucza w panelu PrestaShop |
| `Usługi sieciowe wyłączone` | Web Services nie jest aktywne | Włącz w `Zaawansowane → Usługi sieciowe` |
| `Error 403` przy Google API | Konto usługi nie ma dostępu do GMC | Dodaj e-mail konta usługi w Merchant Center |
| `File not found: service_account.json` | Zły path do pliku JSON | Sprawdź `SERVICE_ACCOUNT_FILE` w konfiguracji |
| Błędne ceny | Cena netto w PrestaShop | Dostosuj `VAT_MULTIPLIER` |
| Puste opisy produktów | Brak `description_short` w PrestaShop | Skrypt użyje `description` lub nazwy produktu jako fallback |
| `429 Too Many Requests` | Zbyt szybkie zapytania | Zwiększ wartość `time.sleep(0.5)` do np. `1.0` |

Szczegółowe logi każdego uruchomienia znajdziesz w pliku `sync.log`.

---

## 📄 Licencja / License

MIT — możesz swobodnie używać, modyfikować i dystrybuować.

---

## 🤝 Wkład / Contributing

Pull requesty i zgłoszenia błędów są mile widziane!
