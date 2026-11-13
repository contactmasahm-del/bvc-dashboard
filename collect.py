import os
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import requests

DATA_PATH = "data/prix_historique.csv"
SCANNER_URL = "https://scanner.tradingview.com/morocco/scan"

def get_bvc_prices():
    payload = {
        "filter": [],
        "options": {"lang": "fr"},
        "columns": ["name", "close", "volume"],
        "range": [0, 200]
    }
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0"
    }

    resp = requests.post(SCANNER_URL, json=payload, headers=headers, timeout=20)
    resp.raise_for_status()
    items = resp.json().get("data", [])

    rows = []
    for item in items:
        d = item.get("d", [])
        if len(d) < 2 or d[0] is None or d[1] is None:
            continue
        ticker = str(d[0]).strip().upper()
        try:
            cours = float(d[1])
            volume = float(d[2]) if len(d) > 2 and d[2] is not None else 0.0
        except (ValueError, TypeError):
            continue

        if cours > 0:
            rows.append({
                "ticker": ticker,
                "cours": cours,
                "volume": volume
            })

    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("Aucune cotation BVC reçue depuis le flux de marché.")
    return df

def main():
    os.makedirs("data", exist_ok=True)
    df_today = get_bvc_prices()

    # Date du jour à l'heure de Casablanca
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

    print(f"[SUCCÈS] {len(df_today)} actions BVC enregistrées pour le {today_ma}.")
    print(df_today[df_today["ticker"].isin(["ATW", "BCP", "IAM", "LHM", "MDP"])].to_string(index=False))

if __name__ == "__main__":
    main()
