import os
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import requests

DATA_PATH = "data/prix_historique.csv"
SCANNER_URL = "https://scanner.tradingview.com/morocco/scan"

SECTOR_MAP = {
    "Finance": "Banques & Finance",
    "Commercial Services": "Services aux entreprises",
    "Communications": "Télécoms",
    "Consumer Non-Durables": "Agroalimentaire & Biens de consommation",
    "Consumer Services": "Loisirs & Hôtellerie",
    "Distribution Services": "Distribution",
    "Electronic Technology": "Technologie & Matériel",
    "Energy Minerals": "Énergie & Pétrole",
    "Health Services": "Santé",
    "Health Technology": "Pharmacie",
    "Industrial Services": "BTP & Ingénierie",
    "Non-Energy Minerals": "Mines & Matériaux",
    "Process Industries": "Chimie & Industrie",
    "Producer Manufacturing": "Équipements & Industrie",
    "Retail Trade": "Distribution Spécialisée",
    "Technology Services": "Logiciels & Services IT",
    "Transportation": "Transport & Ports",
    "Utilities": "Énergie & Services publics",
}

def get_bvc_prices():
    payload = {
        "filter": [],
        "options": {"lang": "fr"},
        "columns": ["name", "description", "close", "change", "volume", "sector"],
        "range": [0, 250]
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    resp = requests.post(SCANNER_URL, json=payload, headers=headers, timeout=25)
    resp.raise_for_status()
    items = resp.json().get("data", [])

    rows = []
    for item in items:
        d = item.get("d", [])
        if len(d) < 3 or d[0] is None or d[2] is None:
            continue
        ticker = str(d[0]).strip().upper()
        societe = str(d[1]).strip() if d[1] else ticker
        try:
            cours = float(d[2])
            variation_pct = float(d[3]) if len(d) > 3 and d[3] is not None else 0.0
            volume = float(d[4]) if len(d) > 4 and d[4] is not None else 0.0
        except (ValueError, TypeError):
            continue

        raw_sector = str(d[5]).strip() if len(d) > 5 and d[5] else "Autre"
        secteur = SECTOR_MAP.get(raw_sector, raw_sector)

        if cours > 0:
            rows.append({
                "ticker": ticker,
                "societe_bvc": societe,
                "secteur_bvc": secteur,
                "cours": cours,
                "variation_pct": round(variation_pct, 2),
                "volume": volume
            })

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("Aucune cotation BVC reçue.")
    return df

def main():
    os.makedirs("data", exist_ok=True)
    df_today = get_bvc_prices()

    today_ma = dt.datetime.now(ZoneInfo("Africa/Casablanca")).date().isoformat()
    df_today.insert(0, "date", today_ma)

    if os.path.exists(DATA_PATH):
        old = pd.read_csv(DATA_PATH)
        combined = pd.concat([old, df_today], ignore_index=True)
    else:
        combined = df_today

    combined.drop_duplicates(subset=["date", "ticker"], keep="last", inplace=True)
    combined.sort_values(["date", "ticker"], inplace=True)
    combined.to_csv(DATA_PATH, index=False)
    print(f"[SUCCÈS] {len(df_today)} sociétés BVC enregistrées pour le {today_ma}.")

if __name__ == "__main__":
    main()
