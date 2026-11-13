import os
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import requests

DATA_PATH = "data/prix_historique.csv"
FD_PATH = "data/fondamentaux.csv"
SCANNER_URL = "https://scanner.tradingview.com/morocco/scan"

# Cours de référence pour les valeurs non encore remontées par le scanner automatique
FALLBACK_PRICES = {
    "GTM": 580.0,
    "CAP": 218.9,
    "VCN": 332.0,
    "T2S": 223.9,
    "CMG": 345.0,
    "REB": 78.0,
    "IBC": 32.5,
}

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
        "range": [0, 300]
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
    old = pd.read_csv(DATA_PATH) if os.path.exists(DATA_PATH) else pd.DataFrame()

    # Complète avec toutes les sociétés définies dans fondamentaux.csv absentes du flux
    if os.path.exists(FD_PATH):
        fd = pd.read_csv(FD_PATH)
        fd["ticker"] = fd["ticker"].astype(str).str.strip().str.upper()
        existing_tickers = set(df_today["ticker"].unique())

        extra_rows = []
        for _, r in fd.iterrows():
            tk = r["ticker"]
            if tk not in existing_tickers:
                last_cours = None
                if not old.empty and tk in old["ticker"].values:
                    last_cours = float(old[old["ticker"] == tk].sort_values("date").iloc[-1]["cours"])
                elif tk in FALLBACK_PRICES:
                    last_cours = FALLBACK_PRICES[tk]

                if last_cours and last_cours > 0:
                    extra_rows.append({
                        "ticker": tk,
                        "societe_bvc": str(r.get("societe", tk)).strip(),
                        "secteur_bvc": str(r.get("secteur", "Autre")).strip(),
                        "cours": last_cours,
                        "variation_pct": 0.0,
                        "volume": 0.0
                    })

        if extra_rows:
            df_today = pd.concat([df_today, pd.DataFrame(extra_rows)], ignore_index=True)

    today_ma = dt.datetime.now(ZoneInfo("Africa/Casablanca")).date().isoformat()
    df_today.insert(0, "date", today_ma)

    combined = pd.concat([old, df_today], ignore_index=True) if not old.empty else df_today
    combined.drop_duplicates(subset=["date", "ticker"], keep="last", inplace=True)
    combined.sort_values(["date", "ticker"], inplace=True)
    combined.to_csv(DATA_PATH, index=False)
    print(f"[SUCCÈS] {len(df_today)} sociétés BVC enregistrées pour le {today_ma}.")

if __name__ == "__main__":
    main()
