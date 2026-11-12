import os
import datetime as dt
import pandas as pd
import requests
from bs4 import BeautifulSoup

DATA_PATH = "data/prix_historique.csv"

def clean_number(val):
    if pd.isna(val):
        return 0.0
    s = str(val).replace("\xa0", "").replace(" ", "").replace(",", ".").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0

def get_prices():
    """
    Récupère les cours quotidiens depuis une page récapitulative des cotations BVC.
    Adaptez l'URL et le mapping des colonnes selon la source retenue (BVC, Le Boursier, Medias24).
    """
    url = "https://www.casablanca-bourse.com/fr/live-market/marche-actions-groupement"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    
    # Extraction des tableaux HTML de la page
    tables = pd.read_html(resp.text)
    if not tables:
        raise ValueError("Aucun tableau de cotation détecté sur la page.")
    
    # Concatène les compartiments (Principal A, B, etc.)
    raw = pd.concat(tables, ignore_index=True)
    
    # Normalisation des noms de colonnes (à ajuster selon l'inspection du tableau)
    raw.columns = [str(c).strip().lower() for c in raw.columns]
    
    # Exemple de mapping standard : Ticker / Instrument, Dernier cours, Volume / Quantité
    df = pd.DataFrame()
    df["ticker"] = raw.iloc[:, 0].astype(str).str.strip().str.upper()
    df["cours"] = raw.iloc[:, 2].apply(clean_number)
    df["volume"] = raw.iloc[:, 5].apply(clean_number)
    
    # Filtre les lignes invalides ou titres sans cotation
    df = df[(df["ticker"].str.len().between(2, 6)) & (df["cours"] > 0)].copy()
    return df

def main():
    os.makedirs("data", exist_ok=True)
    df_today = get_prices()
    df_today["date"] = dt.date.today().isoformat()
    
    if os.path.exists(DATA_PATH):
        old = pd.read_csv(DATA_PATH)
        combined = pd.concat([old, df_today], ignore_index=True)
    else:
        combined = df_today
        
    combined.drop_duplicates(subset=["date", "ticker"], keep="last", inplace=True)
    combined.sort_values(["date", "ticker"], inplace=True)
    combined.to_csv(DATA_PATH, index=False)
    print(f"Mise à jour réussie : {len(df_today)} valeurs enregistrées.")

if __name__ == "__main__":
    main()
