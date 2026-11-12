import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(layout="wide", page_title="Valorisation BVC — Aide à la Décision")

@st.cache_data(ttl=3600)
def load_data():
    px_df = pd.read_csv("data/prix_historique.csv", parse_dates=["date"])
    fd = pd.read_csv("data/fondamentaux.csv")
    return px_df, fd

px_df, fd = load_data()

# Calcul du volume moyen sur les 20 dernières séances (indicateur de liquidité)
px_df = px_df.sort_values(["ticker", "date"])
px_df["vol_moy_20j"] = px_df.groupby("ticker")["volume"].transform(
    lambda s: s.rolling(20, min_periods=1).mean()
)

# Dernière séance disponible
last_date = px_df["date"].max()
last = px_df[px_df["date"] == last_date].merge(fd, on="ticker", how="inner")

# Calculs fondamentaux par action
last["BPA"] = last["resultat_net"] / last["nb_actions"]
last["VCPA"] = last["capitaux_propres"] / last["nb_actions"]
last["Capitalisation (MMAD)"] = (last["cours"] * last["nb_actions"]) / 1e6

# Ratios de valorisation (protection contre les résultats négatifs)
last["PER"] = np.where(last["BPA"] > 0, last["cours"] / last["BPA"], np.nan)
last["P/B"] = np.where(last["VCPA"] > 0, last["cours"] / last["VCPA"], np.nan)
last["Rendement (%)"] = (last["dpa"] / last["cours"]) * 100
last["ROE (%)"] = (last["resultat_net"] / last["capitaux_propres"]) * 100
last["Payout (%)"] = np.where(last["resultat_net"] > 0, (last["dpa"] * last["nb_actions"] / last["resultat_net"]) * 100, np.nan)

# EV/EBITDA (non pertinent pour Banques et Assurances)
is_fin = last["secteur"].str.lower().isin(["banques", "assurances", "sociétés de financement"])
ev = (last["cours"] * last["nb_actions"]) + last["dette_nette"]
last["EV/EBITDA"] = np.where((~is_fin) & (last["ebitda"] > 0), ev / last["ebitda"], np.nan)

# Comparaison vs Médiane Sectorielle
last["PER Secteur"] = last.groupby("secteur")["PER"].transform("median")
last["Décote/Prime PER (%)"] = ((last["PER"] / last["PER Secteur"]) - 1) * 100

# Score composite de valorisation (0 à 100) : favorise PER bas, P/B bas, Rendement élevé, ROE élevé
r_per = last["PER"].rank(ascending=False, pct=True)
r_pb = last["P/B"].rank(ascending=False, pct=True)
r_div = last["Rendement (%)"].rank(ascending=True, pct=True)
r_roe = last["ROE (%)"].rank(ascending=True, pct=True)
last["Score (/100)"] = ((r_per * 0.30 + r_pb * 0.25 + r_div * 0.25 + r_roe * 0.20) * 100).round(1)

# --- BARRE LATÉRALE (FILTRES) ---
st.sidebar.header("Filtres de décision")
secteurs_sel = st.sidebar.multiselect(
    "Secteurs", sorted(last["secteur"].unique()), default=sorted(last["secteur"].unique())
)
min_vol = st.sidebar.number_input("Volume moyen min (titres/jour)", min_value=0, value=0, step=500)
max_per = st.sidebar.slider("PER maximum", min_value=5, max_value=60, value=40)

data = last[
    (last["secteur"].isin(secteurs_sel)) &
    (last["vol_moy_20j"] >= min_vol) &
    ((last["PER"] <= max_per) | (last["PER"].isna()))
].copy()

# --- EN-TÊTE ---
st.title("Dashboard de Valorisation — Bourse de Casablanca")
st.caption(f"Dernière mise à jour des cours : {last_date.strftime('%d/%m/%Y')} | {len(data)} sociétés affichées")

c1, c2, c3, c4 = st.columns(4)
c1.metric("PER Médian (Sélection)", f"{data['PER'].median():.1f}x")
c2.metric("P/B Médian", f"{data['P/B'].median():.2f}x")
c3.metric("Rendement Médian", f"{data['Rendement (%)'].median():.2f} %")
c4.metric("ROE Médian", f"{data['ROE (%)'].median():.1f} %")

tab1, tab2, tab3 = st.tabs(["1. Screener & Opportunités", "2. Comparaison Sectorielle", "3. Duel de Sociétés"])

with tab1:
    cols_show = [
        "ticker", "societe", "secteur", "cours", "Score (/100)",
        "PER", "Décote/Prime PER (%)", "P/B", "EV/EBITDA",
        "Rendement (%)", "ROE (%)", "Payout (%)", "vol_moy_20j"
    ]
    st.dataframe(
        data[cols_show].sort_values("Score (/100)", ascending=False).style.format({
            "cours": "{:.2f}",
            "Score (/100)": "{:.1f}",
            "PER": "{:.1f}x",
            "Décote/Prime PER (%)": "{:+.1f}%",
            "P/B": "{:.2f}x",
            "EV/EBITDA": "{:.1f}x",
            "Rendement (%)": "{:.2f}%",
            "ROE (%)": "{:.1f}%",
            "Payout (%)": "{:.0f}%",
            "vol_moy_20j": "{:,.0f}"
        }, na_rep="-"),
        use_container_width=True,
        hide_index=True
    )
    
    fig_scatter = px.scatter(
        data.dropna(subset=["PER", "Rendement (%)"]),
        x="PER",
        y="Rendement (%)",
        size="Capitalisation (MMAD)",
        color="secteur",
        hover_name="societe",
        hover_data=["P/B", "ROE (%)", "Score (/100)"],
        title="Matrice Valorisation (PER) vs Rendement Dividende"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    sect_df = data.groupby("secteur").agg(
        Sociétés=("ticker", "count"),
        PER_Médian=("PER", "median"),
        PB_Médian=("P/B", "median"),
        EV_EBITDA_Médian=("EV/EBITDA", "median"),
        Rendement_Médian=("Rendement (%)", "median"),
        ROE_Médian=("ROE (%)", "median")
    ).reset_index()
    
    st.dataframe(sect_df.style.format({
        "PER_Médian": "{:.1f}x",
        "PB_Médian": "{:.2f}x",
        "EV_EBITDA_Médian": "{:.1f}x",
        "Rendement_Médian": "{:.2f}%",
        "ROE_Médian": "{:.1f}%"
    }, na_rep="-"), use_container_width=True, hide_index=True)
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(px.bar(sect_df, x="secteur", y="PER_Médian", title="PER Médian par Secteur"), use_container_width=True)
    with col_g2:
        st.plotly_chart(px.bar(sect_df, x="secteur", y="Rendement_Médian", title="Rendement Médian (%) par Secteur"), use_container_width=True)

with tab3:
    choix = st.multiselect(
        "Sélectionnez 2 à 5 sociétés à comparer",
        options=sorted(last["societe"].unique()),
        default=sorted(last["societe"].unique())[:2]
    )
    if choix:
        # Comparaison fondamentale côte à côte
        comp_fd = last[last["societe"].isin(choix)].set_index("societe")[
            ["secteur", "cours", "PER", "P/B", "EV/EBITDA", "Rendement (%)", "ROE (%)", "Payout (%)", "Score (/100)"]
        ].T
        st.subheader("Comparatif Fondamental")
        st.dataframe(comp_fd, use_container_width=True)
        
        # Évolution boursière en Base 100
        hist = px_df.merge(fd[["ticker", "societe"]], on="ticker")
        hist = hist[hist["societe"].isin(choix)].sort_values("date").copy()
        hist["Performance (Base 100)"] = hist.groupby("societe")["cours"].transform(lambda s: (s / s.iloc[0]) * 100)
        
        st.subheader("Évolution Relative des Cours (Base 100)")
        st.plotly_chart(
            px.line(hist, x="date", y="Performance (Base 100)", color="societe"),
            use_container_width=True
        )
