import os
import time
import datetime as dt
import urllib3
import pandas as pd
import casased as cas

# Désactive les avertissements SSL éventuels des serveurs marocains
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_PATH = "data/prix_historique.csv"
FD_PATH = "data/fondamentaux.csv"

# Correspondance entre les tickers BVC et les noms reconnus par l'API
ALIASES = {
    "ATW": ["Attijariwafa", "ATW"],
    "BCP": ["BCP"],
    "BOA": ["BoA", "BOA"],
    "CIH": ["CIH"],
    "CDM": ["CDM"],
    "CFG": ["CFG", "CFG Bank"],
    "IAM": ["IAM", "Maroc Telecom"],
    "TQM": ["TAQA Morocco", "TQM"],
    "LHM": ["Holcim Maroc", "LafargeHolcim", "LHM"],
    "CMA": ["Ciments Maroc", "CMA"],
    "MNG": ["Managem", "MNG"],
    "CMT": ["CMT"],
    "SMI": ["SMI"],
    "AKT": ["Akdital", "AKT"],
    "MDP": ["Marsa Maroc", "SODEP", "MDP"],
    "ADH": ["Addoha", "ADH"],
    "ADI": ["Alliances", "ADI"],
    "RDS": ["Res.Dar Saada", "RDS"],
    "LBV": ["LABEL VIE", "LBV"],
    "CSR": ["COSUMAR", "CSR"],
    "LES": ["Lesieur Cristal", "LES"],
    "MUT": ["Mutandis", "MUT"],
    "HPS": ["HPS"],
    "DYT": ["Disty Technolog", "DYT"],
    "DIS": ["DISWAY", "DIS"],
    "S2M": ["S2M"],
    "M2M": ["M2M Group", "M2M"],
    "TGC": ["TGCC", "TGC"],
    "JET": ["Jet Contractors", "JET"],
    "SGT": ["SGTM", "SGT"],
    "WAA": ["Wafa Assur", "WAA"],
    "ATL": ["ATLANTASANAD", "ATL"],
    "SAH": ["Sanlam Maroc", "SAH"],
    "AFM": ["AFMA", "AFM"],
    "RIS": ["Risma", "RIS"],
    "COL": ["Colorado", "COL"],
    "SNP": ["SNEP", "SNP"],
    "CMG": ["CMGP GROUP", "CMG"],
}

def fetch_ticker_history(ticker, societe, start_date):
    candidates = ALIASES.get(ticker, []) + [ticker, societe]
    # Supprime les doublons tout en gardant l'ordre
    candidates = list(dict.fromkeys([c for c in candidates if pd.notna(c)]))

    for name in candidates:
        try:
            df = cas.get_history(name, start=start_date)
            if df is not None and not df.empty:
                df = df.reset_index()
                date_col = df.columns[0]
                out = pd.DataFrame()
                out["date"] = pd.to_datetime(df[date_col]).dt.strftime("%Y-%m-%d")
                out["ticker"] = ticker
                out["cours"] = pd.to_numeric(df["Value"], errors="coerce")
                out["volume"] = pd.to_numeric(df.get("Volume", 0), errors="coerce").fillna(0)
                out = out.dropna(subset=["cours"])
                out = out[out["cours"] > 0]
                if not out.empty:
                    return out
        except Exception:
            continue
    return pd.DataFrame()

def main():
    os.makedirs("data", exist_ok=True)
    fd = pd.read_csv(FD_PATH)

    # Si aucun historique n'existe encore, on récupère les 180 derniers jours ; sinon les 10 derniers jours
    lookback_days = 10 if os.path.exists(DATA_PATH) else 180
    start_date = (dt.date.today() - dt.timedelta(days=lookback_days)).isoformat()

    frames = []
    for _, row in fd.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        societe = str(row["societe"]).strip()
        df_t = fetch_ticker_history(ticker, societe, start_date)
        if not df_t.empty:
            print(f"[OK] {ticker} ({societe}) : {len(df_t)} séances récupérées")
            frames.append(df_t)
        else:
            print(f"[AVERTISSEMENT] Aucune donnée trouvée pour {ticker} ({societe})")
        time.sleep(0.5)

    if not frames:
        raise RuntimeError("Aucune cotation n'a pu être récupérée pour les valeurs du fichier fondamentaux.csv.")

    new_data = pd.concat(frames, ignore_index=True)

    if os.path.exists(DATA_PATH):
        old = pd.read_csv(DATA_PATH)
        combined = pd.concat([old, new_data], ignore_index=True)
    else:
        combined = new_data

    combined.drop_duplicates(subset=["date", "ticker"], keep="last", inplace=True)
    combined.sort_values(["date", "ticker"], inplace=True)
    combined.to_csv(DATA_PATH, index=False)
    print(f"Sauvegarde terminée : {len(combined)} lignes au total dans {DATA_PATH}.")

if __name__ == "__main__":
    main()
