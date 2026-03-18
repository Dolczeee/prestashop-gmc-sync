# 🛒 PrestaShop → Google Merchant Center Sync

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![PrestaShop](https://img.shields.io/badge/PrestaShop-1.7%20%2F%208.x-DF0067?logo=prestashop&logoColor=white)
![Google Shopping](https://img.shields.io/badge/Google%20Merchant%20Center-Content%20API%20v2.1-4285F4?logo=google&logoColor=white)
![Maintenance](https://img.shields.io/badge/Maintained-yes-brightgreen)
![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen)

A Python script for automatic product synchronization from PrestaShop to Google Merchant Center (Google Shopping).

> Compatible with PrestaShop 1.7 / 8.x and Google Content API v2.1.  
> No paid tools or plugins required.

🇵🇱 [Polska wersja instrukcji → README.pl.md](README.pl.md)

---

## 📋 Table of Contents

- [Requirements](#-requirements)
- [Installation](#-installation)
- [Step 1 — PrestaShop API Key](#step-1--prestashop-api-key)
- [Step 2 — Google Service Account](#step-2--google-service-account)
- [Step 3 — Merchant ID](#step-3--merchant-id)
- [Step 4 — Script Configuration](#step-4--script-configuration)
- [Running the Script](#%EF%B8%8F-running-the-script)
- [Sync Modes](#-sync-modes)
- [Category Mapping](#%EF%B8%8F-category-mapping)
- [Troubleshooting](#-troubleshooting)

---

## ✅ Requirements

- Python **3.8+**
- Access to the PrestaShop admin panel
- A Google Merchant Center account
- A Google Cloud Console project

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/prestashop-gmc-sync.git
cd prestashop-gmc-sync

# Install dependencies
pip install requests google-auth google-api-python-client
```

---

## Step 1 — PrestaShop API Key

The API key allows the script to read products from your store.

1. Log in to your **PrestaShop admin panel**.
2. Go to: `Advanced Parameters` → `Webservice`.

   > If you don't see this option, try: `Configure` → `Advanced Parameters` → `Webservice`.

3. Make sure the webservice is **enabled** (toggle at the top of the page).
4. Click **"Add new key"** (the `+` icon).
5. Set permissions — the script only needs **read (GET)** access. Check `GET` for:
   - `products`
   - `categories`
   - `images`
6. Add a description, e.g. `GMC Sync`.
7. Click **Save**.
8. Copy the generated key (a long string of characters) — this is your `PRESTA_KEY`.

> ⚠️ The key is only shown once after creation — save it immediately!

---

## Step 2 — Google Service Account

The script uses server-to-server authentication — no browser login required.

### 2a. Create a project in Google Cloud Console

1. Go to [console.cloud.google.com](https://console.cloud.google.com).
2. Click **"Select a project"** → **"New Project"**.
3. Give it any name, e.g. `gmc-sync`.
4. Click **Create**.

### 2b. Enable the Content API for Shopping

1. In the left menu: `APIs & Services` → `Library`.
2. Search for **"Content API for Shopping"**.
3. Click the result and select **Enable**.

### 2c. Create a Service Account

1. Go to: `APIs & Services` → `Credentials`.
2. Click **"Create Credentials"** → **"Service Account"**.
3. Give it a name, e.g. `gmc-sync-account`, click **Create and Continue**.
4. Skip the permissions section (click **Continue** → **Done**).
5. In the service accounts list, click on the newly created account.
6. Go to the **Keys** tab → **Add Key** → **Create New Key**.
7. Select **JSON** format → **Create**.
8. The `.json` file will be downloaded automatically — **place it in the script folder** and update the `SERVICE_ACCOUNT_FILE` variable in `prestashop_to_gmc.py`.

### 2d. Link the Service Account to Merchant Center

1. Copy the service account's email address (visible in Google Cloud Console, format: `name@project.iam.gserviceaccount.com`).
2. Go to [merchants.google.com](https://merchants.google.com).
3. Click the ⚙️ icon (Settings) → **Account access**.
4. Click **"Add user"**.
5. Paste the service account email, select the **Admin** or **Standard** role.
6. Click **Add user**.

> ✅ The script now has access to your Merchant Center.

---

## Step 3 — Merchant ID

1. Log in to [merchants.google.com](https://merchants.google.com).
2. Your **Merchant ID** is visible:
   - In the top right corner next to your store name,
   - or under `⚙️ Settings` → `Account information`.
3. It is a multi-digit number, e.g. `123456789`.

---

## Step 4 — Script Configuration

Open `prestashop_to_gmc.py` and fill in the configuration section at the top:

```python
MERCHANT_ID          = '123456789'          # Your Merchant ID from Google Merchant Center
PRESTA_KEY           = 'ABCDEF1234567890'   # API key from PrestaShop
DOMAIN               = 'yourstore.com'      # Domain without https:// and without trailing /
SERVICE_ACCOUNT_FILE = 'service_account.json'  # Name of the JSON file downloaded from Google Cloud

CURRENCY             = 'EUR'   # Currency: PLN, EUR, USD, GBP...
TARGET_COUNTRY       = 'DE'    # Target country (ISO): PL, DE, FR, GB...
LANGUAGE_CODE        = 'de'    # Product language: pl, de, en...

VAT_MULTIPLIER       = 1.19    # VAT rate: 1.23 = 23%, 1.19 = 19%, 1.0 = no VAT

DEFAULT_BRAND        = 'My Brand'     # Default product brand
DEFAULT_GOOGLE_CATEGORY = '216'       # Default Google category (see section below)
```

### Directory structure after configuration

```
prestashop-gmc-sync/
├── prestashop_to_gmc.py
├── service_account.json   ← downloaded from Google Cloud Console
├── prestashop_to_gmc.log  ← created automatically after the first run
└── README.md
```

> ⚠️ Add `service_account.json` to `.gitignore` — never upload private keys to GitHub!

---

## ▶️ Running the Script

```bash
python prestashop_to_gmc.py
```

The script will display a list of categories from your store, then ask:
1. **Which category** to sync (or all of them).
2. **Sync mode** (see below).

---

## 🔄 Sync Modes

| Mode | Description |
|------|-------------|
| `1` — Full sync | Sends all products. Existing entries in GMC are overwritten. |
| `2` — New only | Skips products that already exist in GMC. Useful for partial catalog migrations. |
| `3` — Update only | Sends only products that are already present in GMC. Does not add new ones. |

---

## 🗂️ Category Mapping

Google requires each product to be assigned to a category from the Google taxonomy.  
You can map your PrestaShop categories to Google category numbers:

```python
CATEGORY_MAP = {
    '12': '436',    # PrestaShop category ID → Google category number
    '15': '2271',
    '8':  '111',
}
```

Full list of Google category numbers:  
🔗 [taxonomy-with-ids.en-US.txt](https://www.google.com/basepages/producttype/taxonomy-with-ids.en-US.txt)

If a category is not mapped, `DEFAULT_GOOGLE_CATEGORY` will be used as a fallback.

---

## 🔍 Troubleshooting

| Problem | Likely cause | Solution |
|---------|-------------|----------|
| `403 Forbidden` on PrestaShop | API key missing GET permissions | Check key permissions in the PrestaShop panel |
| `Webservice disabled` | Web Services not active | Enable in `Advanced Parameters → Webservice` |
| `Error 403` on Google API | Service account has no access to GMC | Add the service account email in Merchant Center |
| `File not found: service_account.json` | Wrong path to JSON file | Check `SERVICE_ACCOUNT_FILE` in the config |
| Wrong prices | PrestaShop stores net prices | Adjust `VAT_MULTIPLIER` accordingly |
| Empty product descriptions | No `description_short` in PrestaShop | Script falls back to `description` or product name |
| `429 Too Many Requests` | Requests sent too fast | Increase `time.sleep(0.5)` to e.g. `1.0` |

Detailed logs for each run are saved in `prestashop_to_gmc.log`.

---

## 📄 License

MIT — free to use, modify and distribute.

---

## 🤝 Contributing

Pull requests and bug reports are welcome!
