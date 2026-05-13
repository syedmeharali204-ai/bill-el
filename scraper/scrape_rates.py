"""
Pakistan Electricity Tariff Scraper
Sources:
  1. NEPRA official website (HTML pages)
  2. IESCO tariff guide page (has SRO-wise rate tables)
  3. Fallback: hardcoded latest known rates (SRO 279(I)/2026)

Runs daily via GitHub Actions → saves to data/rates.json
"""

import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timezone

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Cache-Control": "max-age=0",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "rates.json")

# Latest known rates (SRO No. 279(I)/2026 — February 2026)
# Source: NEPRA / IESCO Tariff Guide
# These are BASE rates (excl. GST, FPA, surcharges)
FALLBACK_RATES = {
    "sro": "279(I)/2026",
    "effective_from": "2026-02-01",
    "source": "verified_SRO_279_2026",
    "domestic_A1": {
        "description": "General Supply Tariff - Residential (A-1)",
        "lifeline": [
            {"slab": "1-50 units",   "rate_pkr": 3.95,  "type": "lifeline"},
            {"slab": "51-100 units", "rate_pkr": 7.74,  "type": "lifeline"},
        ],
        "protected": [
            {"slab": "1-100 units",   "rate_pkr": 10.54, "type": "protected"},
            {"slab": "101-200 units",  "rate_pkr": 13.01, "type": "protected"},
        ],
        "unprotected": [
            {"slab": "1-100 units",   "rate_pkr": 22.44, "type": "unprotected"},
            {"slab": "101-200 units", "rate_pkr": 28.91, "type": "unprotected"},
            {"slab": "201-300 units", "rate_pkr": 33.10, "type": "unprotected"},
            {"slab": "301-400 units", "rate_pkr": 36.46, "type": "unprotected"},
            {"slab": "401-500 units", "rate_pkr": 38.95, "type": "unprotected"},
            {"slab": "501-600 units", "rate_pkr": 40.22, "type": "unprotected"},
            {"slab": "601-700 units", "rate_pkr": 41.85, "type": "unprotected"},
            {"slab": "700+ units",    "rate_pkr": 47.69, "type": "unprotected"},
        ],
        "fixed_charges_pkr_month": {
            "single_phase": 75,
            "three_phase": 150
        }
    },
    "notes": [
        "Rates are BASE TARIFF only — exclude GST (17%), FPA, FC Surcharge, NJ Surcharge, PTV Fee",
        "Protected = consumers using <= 200 units/month for last 6 months",
        "Lifeline = very low income registered consumers",
        "FPA changes monthly — check NEPRA for current month FPA",
        "Verified: SRO 279(I)/2026 via IESCO live + NEPRA + Daily Pakistan Jan 2026"
    ]
}


# ──────────────────────────────────────────────
# SCRAPER 1: Try IESCO tariff guide page
# ──────────────────────────────────────────────
def scrape_iesco_tariff():
    """
    IESCO publishes tariff guide on their website.
    URL: https://www.iesco.com.pk/tariff-guide
    They update it with each new SRO.
    """
    url = "https://www.iesco.com.pk/tariff-guide"
    print(f"[1] Trying IESCO tariff guide: {url}")
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for SRO number mentioned on page
        page_text = soup.get_text()
        sro_match = re.search(r"S\.?R\.?O\.?\s*No\.?\s*([\d]+\([IiVv]+\)/\d{4})", page_text)
        sro = sro_match.group(1) if sro_match else "unknown"

        # Look for tables with rate data
        tables = soup.find_all("table")
        rate_tables = []
        for table in tables:
            text = table.get_text()
            if any(kw in text for kw in ["unit", "Unit", "kWh", "Lifeline", "Protected"]):
                rows = []
                for tr in table.find_all("tr"):
                    cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
                    if cols:
                        rows.append(cols)
                if rows:
                    rate_tables.append(rows)

        if rate_tables:
            print(f"   ✅ Found {len(rate_tables)} rate table(s) on IESCO. SRO: {sro}")
            return {
                "source": "iesco_website",
                "sro": sro,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
                "raw_tables": rate_tables[:3],  # max 3 tables
                "url": url
            }
        else:
            print("   ⚠️  No rate tables found on IESCO page")
            return None

    except Exception as e:
        print(f"   ❌ IESCO scrape failed: {e}")
        return None


# ──────────────────────────────────────────────
# SCRAPER 2: Try NEPRA news page for latest FCA
# ──────────────────────────────────────────────
def scrape_nepra_latest_fca():
    """
    NEPRA publishes monthly FCA on their news page.
    We grab the latest FCA notification link.
    """
    url = "https://nepra.org.pk/news.php"
    print(f"[2] Trying NEPRA news page: {url}")
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find links related to Fuel Charges Adjustment
        fca_links = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            if any(kw in text for kw in ["Fuel Charges Adjustment", "FCA", "Fuel Cost"]):
                full_url = href if href.startswith("http") else f"https://nepra.org.pk/{href.lstrip('/')}"
                fca_links.append({"title": text, "url": full_url})

        if fca_links:
            latest = fca_links[0]
            print(f"   ✅ Found latest FCA notification: {latest['title']}")
            return {
                "source": "nepra_news",
                "latest_fca_title": latest["title"],
                "latest_fca_url": latest["url"],
                "scraped_at": datetime.now(timezone.utc).isoformat()
            }
        else:
            print("   ⚠️  No FCA links found on NEPRA news page")
            return None

    except Exception as e:
        print(f"   ❌ NEPRA scrape failed: {e}")
        return None


# ──────────────────────────────────────────────
# SCRAPER 3: Try NEPRA tariff page for LESCO/FESCO
# ──────────────────────────────────────────────
def scrape_nepra_disco_page(disco="LESCO"):
    """
    Scrape NEPRA distribution company tariff page
    """
    url = f"https://nepra.org.pk/tariff/Distribution%20{disco}.php"
    print(f"[3] Trying NEPRA {disco} page: {url}")
    try:
        resp = SESSION.get(url, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # Find all notification/SRO links (PDFs)
        pdf_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)
            if ".pdf" in href.lower() and "2025" in href or "2026" in href:
                full_url = href if href.startswith("http") else f"https://nepra.org.pk/{href.lstrip('/')}"
                pdf_links.append({"title": text or href.split("/")[-1], "url": full_url})

        print(f"   ✅ Found {len(pdf_links)} recent PDF(s) for {disco}")
        return {
            "source": f"nepra_{disco.lower()}_page",
            "disco": disco,
            "recent_pdfs": pdf_links[:5],
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "url": url
        }

    except Exception as e:
        print(f"   ❌ NEPRA {disco} scrape failed: {e}")
        return None


# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Pakistan Electricity Tariff Scraper")
    print(f"  Run time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 55)

    result = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "scrape_status": {},
        "tariff_rates": FALLBACK_RATES,   # Always include known rates
        "live_data": {}
    }

    # --- Run all scrapers ---
    iesco_data = scrape_iesco_tariff()
    if iesco_data:
        result["live_data"]["iesco"] = iesco_data
        result["scrape_status"]["iesco"] = "success"
    else:
        result["scrape_status"]["iesco"] = "failed"

    fca_data = scrape_nepra_latest_fca()
    if fca_data:
        result["live_data"]["nepra_fca"] = fca_data
        result["scrape_status"]["nepra_fca"] = "success"
    else:
        result["scrape_status"]["nepra_fca"] = "failed"

    lesco_data = scrape_nepra_disco_page("LESCO")
    if lesco_data:
        result["live_data"]["lesco"] = lesco_data
        result["scrape_status"]["lesco"] = "success"
    else:
        result["scrape_status"]["lesco"] = "failed"

    # --- Save output ---
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 55)
    print(f"  ✅ Data saved to: {OUTPUT_FILE}")
    print(f"  Scrape status: {result['scrape_status']}")
    print("=" * 55)


if __name__ == "__main__":
    main()
