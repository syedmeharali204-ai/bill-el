# 🇵🇰 Pakistan Electricity Tariff Scraper

Auto-scrapes NEPRA & DISCO electricity rates daily via GitHub Actions.

## 📁 Project Structure

```
├── .github/
│   └── workflows/
│       └── daily_scrape.yml   ← GitHub Actions (runs daily 6 AM PKT)
├── scraper/
│   ├── scrape_rates.py        ← Main Python scraper
│   └── requirements.txt       ← Dependencies
├── data/
│   └── rates.json             ← Output (auto-updated daily)
└── README.md
```

## ✅ Features

- Runs **every day at 6 AM Pakistan time** automatically
- Scrapes **NEPRA** + **IESCO** + **LESCO** pages
- Saves latest rates to `data/rates.json`
- **Public repo = Unlimited GitHub Actions minutes (Free)**
- Falls back to latest known SRO rates if scraping fails

## 🔗 Data Sources

| Source | URL |
|--------|-----|
| NEPRA Official | https://nepra.org.pk |
| IESCO Tariff Guide | https://iesco.com.pk/tariff-guide |
| NEPRA LESCO Page | https://nepra.org.pk/tariff/Distribution%20LESCO.php |

## 📊 Latest Rates (SRO 279(I)/2026)

### Domestic A-1 Base Tariff (excl. taxes)

| Slab | Type | Rate (Rs/unit) |
|------|------|---------------|
| 1-50 units | Lifeline | 3.95 |
| 51-100 units | Lifeline | 7.74 |
| 1-100 units | Protected | 10.54 |
| 101-200 units | Protected | 16.48 |
| 1-100 units | Unprotected | 23.59 |
| 101-200 units | Unprotected | 30.10 |
| 201-300 units | Unprotected | 34.26 |
| 301-400 units | Unprotected | 39.15 |
| 401-500 units | Unprotected | 41.36 |
| 501-600 units | Unprotected | 42.78 |
| 601-700 units | Unprotected | 43.92 |
| 700+ units | Unprotected | 48.84 |

> ⚠️ Add GST (17%) + FPA (monthly variable) + surcharges for final amount

## 🚀 Setup (Fork & Use)

1. Fork this repo (make sure it stays **Public**)
2. GitHub Actions will auto-run daily
3. Manual run: Go to **Actions** → **Daily Electricity Tariff Scraper** → **Run workflow**

## 📡 Use rates.json as Free API

Once repo is public, you can fetch rates directly:

```javascript
const res = await fetch(
  'https://raw.githubusercontent.com/YOUR_USERNAME/pakistan-electricity-scraper/main/data/rates.json'
);
const data = await res.json();
console.log(data.tariff_rates.domestic_A1.unprotected);
```

## 📝 Notes

- FPA (Fuel Price Adjustment) changes every month — always check NEPRA for current month FPA
- These are national uniform tariff rates (LESCO, FESCO, IESCO, MEPCO all same base)
- K-Electric (Karachi) has different rates

## 📜 License

MIT — Free to use
