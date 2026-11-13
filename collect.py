import os
import time
import datetime as dt
import urllib3
import pandas as pd
import casased as cas

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_PATH = "data/prix_historique.csv"
FD_PATH = "data/fondamentaux.csv"

ALIASES = {
    "ATW": ["Attijariwafa", "ATW"],
    "BCP": ["BCP"],
    "BOA": ["BoA", "BOA"],
    "CIH": ["CIH"],
    "CDM": ["CDM"],
    "CFG": ["CFG", "CFG Bank"],
    "IAM": ["IAM", "Maroc Telecom"],
    "TQM": ["TAQA Morocco", "TQM"],
    "LHM": ["LafargeHolcim", "Holcim Maroc", "LHM"],
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

def extract_ohlcv(df, ticker):
    if not isinstance(df.index, pd.RangeIndex):
        df = df.reset_index()

    cols_lower = {str(c).lower().strip(): c for c in df.columns}

    # Détection de la colonne date
    date_col = next((cols_lower[k] for k in ["date", "index", "jour"] if k in cols_lower), df.columns[0])

    # Détection de la colonne cours
    price_col = next(
        (cols_lower[k] for k in ["value", "close", "cours", "price", "dernier"] if k in cols_lower),
        None
    )
    if price_col is None:
        numeric_cols = [c for c in df.columns if c != date_col and "vol" not in str(c).lower()]
        if not numeric_cols:
            return pd.DataFrame()
        price_col = numeric_cols[0]

    # Détection de la colonne volume
    vol_col = next(
        (cols_lower[k] for k in ["volume", "quantite", "quantité", "qte"] if k in cols_lower),
        None
    )

    out = pd.DataFrame()
    out["date"] = pd.to_datetime(df[date_col], errors="coerce").dt.strftime("%Y-%m-%d")
    out["ticker"] = ticker
    out["cours"] = pd.to_numeric(df[price_col], errors="coerce")
    out["volume"] = pd.to_numeric(df[vol_col], errors="coerce").fillna(0) if vol_col else 0.0

    out = out.dropna(subset=["date", "cours"])
    out = out[out["cours"] > 0]
    return out

def fetch_ticker_history(ticker, societe, start_dt, end_dt):
    candidates = ALIASES.get(ticker, []) + [ticker, societe]
    candidates = list(dict.fromkeys([c for c in candidates if pd.notna(c)]))

    for name in candidates:
        for s_arg, e_arg in [
            (start_dt, end_dt),
            (start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d")),
        ]:
            try:
                df = cas.get_history(name, start=s_arg, end=e_arg)
                if df is not None and not df.empty:
                    out = extract_ohlcv(df, ticker)
                    if not out.empty:
                        return out
            except Exception:
                continue
    return pd.DataFrame()

def main():
    os.makedirs("data", exist_ok=True)
    fd = pd.read_csv(FD_PATH)

    lookback_days = 10 if os.path.exists(DATA_PATH) else 180
    end_dt = dt.datetime.now()
    start_dt = end_dt - dt.timedelta(days=lookback_days)

    frames = []
    for _, row in fd.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        societe = str(row["societe"]).strip()
        df_t = fetch_ticker_history(ticker, societe, start_dt, end_dt)
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
