import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from sahm_engine import compute_company_metrics, run_dcf_model, compute_sahm_scores
from sahm_interpreter import INDICATOR_META, inspect_indicator, evaluate_analytical_chains
from sahm_pdf import generate_sahm_pdf

st.set_page_config(layout="wide", page_title="SAHM — Equity Valuation Dashboard BVC", page_icon="📊")

# --- GESTION DU THÈME LIGHT / DARK MODE (PALETTE SAHM) ---
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "selected_indicator" not in st.session_state:
    st.session_state.selected_indicator = "per"

with st.sidebar:
    st.markdown("### 🏛️ SAHM ANALYTICS")
    st.caption("Bourse de Casablanca (BVC)")
    st.session_state.dark_mode = st.toggle("🌙 Mode Sombre (Dark Mode)", value=st.session_state.dark_mode)

if st.session_state.dark_mode:
    BG_MAIN, BG_CARD, TXT_MAIN, TXT_SUB, BORDER_COL = "#0B1120", "#172554", "#F8FAFC", "#CBD5E1", "#334155"
else:
    BG_MAIN, BG_CARD, TXT_MAIN, TXT_SUB, BORDER_COL = "#F1F5F9", "#FFFFFF", "#172554", "#475569", "#CBD5E1"

st.markdown(f"""
<style>
    .stApp {{ background-color: {BG_MAIN}; color: {TXT_MAIN}; }}
    .sahm-card {{
        background-color: {BG_CARD};
        border: 1px solid {BORDER_COL};
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        box-shadow: 0 2px 6px rgba(23, 37, 84, 0.06);
    }}
    .sahm-badge {{
        display: inline-block;
        padding: 3px 10px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        color: #FFFFFF;
    }}
    .sahm-title {{ color: {TXT_MAIN}; font-weight: 800; margin-bottom: 4px; }}
    .sahm-sub {{ color: {TXT_SUB}; font-size: 13px; }}
</style>
""", unsafe_allow_html=True)

# --- CHARGEMENT & FUSION DE 100 % DES SOCIÉTÉS BVC ---
@st.cache_data(ttl=1800)
def load_all_bvc():
    px_df = pd.read_csv("data/prix_historique.csv", parse_dates=["date"])
    fd_df = pd.read_csv("data/fondamentaux.csv")
    px_df["ticker"] = px_df["ticker"].astype(str).str.strip().str.upper()
    fd_df["ticker"] = fd_df["ticker"].astype(str).str.strip().str.upper()

    last_date = px_df["date"].max()
    last_px = px_df[px_df["date"] == last_date].copy()

    # Fusion LEFT depuis les prix BVC pour inclure TOUTES les sociétés cotées
    merged = last_px.merge(fd_df, on="ticker", how="left")
    merged["societe_aff"] = merged["societe"].fillna(merged.get("societe_bvc", merged["ticker"]))
    merged["secteur_aff"] = merged["secteur"].fillna(merged.get("secteur_bvc", "Non classé"))
    if "variation_pct" not in merged.columns:
        merged["variation_pct"] = 0.0
    return px_df, fd_df, merged, last_date

px_df, fd_df, all_df, last_date = load_all_bvc()

# Pré-calcul des médianes sectorielles sur les sociétés disposant de fondamentaux
all_metrics_list = [compute_company_metrics(r) for _, r in all_df.iterrows()]
metrics_df = pd.DataFrame(all_metrics_list)
metrics_df["secteur_aff"] = all_df["secteur_aff"].values
sector_medians_all = metrics_df.groupby("secteur_aff")[["per", "pbr", "pfcf", "ev_ebitda", "roe", "rendement_div"]].median().to_dict("index")

# --- SÉLECTEUR D'ENTREPRISE & NAVIGATION LATÉRALE ---
with st.sidebar:
    st.divider()
    options_labels = [f"{r['ticker']} — {r['societe_aff']} ({r['secteur_aff']})" for _, r in all_df.sort_values("ticker").iterrows()]
    label_to_ticker = {lbl: lbl.split(" — ")[0] for lbl in options_labels}
    selected_label = st.selectbox(
        f"🔍 Rechercher une société BVC ({len(all_df)} cotées)",
        options=options_labels,
        index=0
    )
    sel_ticker = label_to_ticker[selected_label]

    st.divider()
    NAV_ITEMS = [
        "1. Overview",
        "2. Fundamental Analysis",
        "3. Valuation Multiples",
        "4. Dividend Analysis",
        "5. Financial Structure",
        "6. Intrinsic Valuation",
        "7. Comparative Valuation",
        "8. Scenarios & Sensitivity Analysis",
        "9. Investment Decision",
        "10. Research Report",
    ]
    active_page = st.radio("Navigation SAHM", NAV_ITEMS)

row = all_df[all_df["ticker"] == sel_ticker].iloc[0]
sec_med = sector_medians_all.get(row["secteur_aff"], {})
metrics = compute_company_metrics(row, sec_med)

# Paramètres DCF par défaut
default_dcf_params = {
    "rf": 3.5, "erp": 6.5, "kd": 5.0, "tax": 32.0,
    "g_ca": 6.0, "marge_ebit": 18.0, "capex_pct": 6.0, "bfr_pct": 1.5,
    "g_term": 2.5, "horizon": 5
}
if metrics["has_fundamentals"] and not metrics["est_financiere"] and pd.notna(row.get("ca_n")) and row["ca_n"] > 0:
    if pd.notna(row.get("ebit")):
        default_dcf_params["marge_ebit"] = float(np.clip((row["ebit"] / row["ca_n"]) * 100, 3.0, 60.0))
    if pd.notna(row.get("capex")):
        default_dcf_params["capex_pct"] = float(np.clip((row["capex"] / row["ca_n"]) * 100, 1.0, 35.0))

dcf_res = run_dcf_model(row, metrics, default_dcf_params)
scores = compute_sahm_scores(row, metrics, dcf_res, sec_med)
chains, contradictions = evaluate_analytical_chains(metrics, dcf_res)

# --- EN-TÊTE PERMANENT DE LA SOCIÉTÉ ---
var_val = float(row.get("variation_pct", 0.0) or 0.0)
var_color = "#00BF63" if var_val > 0 else ("#EF4444" if var_val < 0 else "#64748B")
capi_str = f"{metrics['capi']/1e6:,.0f} MMAD" if pd.notna(metrics["capi"]) else "N/A"
nb_act_str = f"{int(row['nb_actions']):,}" if pd.notna(row.get("nb_actions")) else "N/A"

st.markdown(f"""
<div class="sahm-card">
    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px;">
        <div>
            <span class="sahm-badge" style="background-color:#4E4C9B;">{row['secteur_aff']}</span>
            <span class="sahm-badge" style="background-color:#172554;">Ticker : {row['ticker']}</span>
            <h2 class="sahm-title" style="margin-top:6px;">{row['societe_aff']}</h2>
            <span class="sahm-sub">Mise à jour : {last_date.strftime('%d/%m/%Y')} | Source : {row.get('source', 'Bourse de Casablanca')} ({row.get('statut_donnees', 'Marché')})</span>
        </div>
        <div style="text-align:right;">
            <div style="font-size:28px; font-weight:800; color:{TXT_MAIN};">{row['cours']:,.2f} MAD</div>
            <div style="font-size:15px; font-weight:700; color:{var_color};">{var_val:+.2f} % aujourd'hui</div>
            <div class="sahm-sub">Capi : <b>{capi_str}</b> | Titres : <b>{nb_act_str}</b></div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- FONCTION D'AFFICHAGE DES CARTES CLIQUABLES + PANNEAU D'INTERPRÉTATION ---
def render_clickable_indicators(keys_list):
    cols = st.columns(len(keys_list))
    for idx, k in enumerate(keys_list):
        val = metrics.get(k, np.nan)
        meta = INDICATOR_META[k]
        val_txt = f"{val:.2f}{meta['unit']}" if pd.notna(val) else "N/A"
        with cols[idx]:
            if st.button(f"🔎 {meta['nom']}\n**{val_txt}**", key=f"btn_{active_page}_{k}", use_container_width=True):
                st.session_state.selected_indicator = k

    # Fiche d'interprétation interactive en 14 points
    sel_k = st.session_state.selected_indicator if st.session_state.selected_indicator in INDICATOR_META else keys_list[0]
    info = inspect_indicator(sel_k, metrics.get(sel_k, np.nan), row, metrics, sec_med)
    with st.expander(f"📘 Fiche d'interprétation intelligente : {info['nom']} ({info['valeur_str']}) — Diagnostic : {info['diagnostic']}", expanded=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown(f"**1. Valeur calculée :** `{info['valeur_str']}`  |  **2. Formule :** `{info['formule']}`")
            st.markdown(f"**3. Définition :** {info['definition']}")
            st.markdown(f"**4. Signification économique :** {info['signification']}")
            st.info(f"**5. Interprétation automatique SAHM :** {info['interpretation']}")
            st.warning(f"**6. Point de vigilance :** {info['vigilance']}")
        with c2:
            st.markdown(f"<span class='sahm-badge' style='background-color:{info['color']};'>Diagnostic : {info['diagnostic']}</span>", unsafe_allow_html=True)
            st.markdown(f"**7. Comparaison secteur :** {info['comp_secteur']}")
            st.markdown(f"**8. Comparaison historique :** {info['comp_historique']}")
            st.markdown(f"**9. Indicateurs liés :** {', '.join(info['lies'])}")
            st.markdown(f"**10. Source & Fiabilité :** {info['source']} ({info['date_maj']}) — Confiance : *{info['confiance']}*")

# ==============================================================================
# NAVIGATION ENTRE LES 10 RUBRIQUES
# ==============================================================================
if active_page == "1. Overview":
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fundamental Score (Qualité)", f"{scores['fundamental_score']}/100" if scores["fundamental_score"] else "N/A")
    c2.metric("Valuation Signal (Prix)", f"{scores['valuation_score']}/100" if scores["valuation_score"] else "N/A", scores["valuation_signal"])
    c3.metric("Valeur Intrinsèque Estimée", f"{dcf_res['vi_action']:.2f} MAD" if dcf_res.get("valid") and pd.notna(dcf_res.get("vi_action")) else "N/A")
    c4.metric("Marge de Sécurité", f"{dcf_res['marge_securite']:+.1f} %" if dcf_res.get("valid") and pd.notna(dcf_res.get("marge_securite")) else "N/A")

    st.subheader("Indicateurs Clés (Cliquez sur un ratio pour ouvrir son diagnostic complet)")
    render_clickable_indicators(["per", "pbr", "roe", "rendement_div"])

    st.subheader("Chaînes d'Analyse & Cohérence des Signaux")
    if contradictions:
        for ct in contradictions:
            st.error(f"⚠️ {ct}")
    for ch in chains:
        st.markdown(f"**{ch['titre']}** — *{ch['statut']}* : {ch['analyse']}")

    st.subheader("Cote Complète de la Bourse de Casablanca (Toutes les valeurs)")
    overview_tbl = all_df[["ticker", "societe_aff", "secteur_aff", "cours", "variation_pct", "volume"]].copy()
    overview_tbl.columns = ["Ticker", "Société", "Secteur", "Cours (MAD)", "Var. Jour (%)", "Volume"]
    st.dataframe(overview_tbl.sort_values("Ticker"), use_container_width=True, hide_index=True)

elif active_page == "2. Fundamental Analysis":
    st.subheader("Performance Financière & Rentabilité")
    render_clickable_indicators(["roe", "roa", "marge_nette"])
    if metrics["has_fundamentals"]:
        f_cols = st.columns(4)
        f_cols[0].metric("Croissance CA (N/N-1)", f"{metrics['croissance_ca']:+.1f} %" if pd.notna(metrics["croissance_ca"]) else "N/A")
        f_cols[1].metric("Croissance Résultat Net", f"{metrics['croissance_rn']:+.1f} %" if pd.notna(metrics["croissance_rn"]) else "N/A")
        f_cols[2].metric("CAGR Résultat Net (3 ans)", f"{metrics['cagr_rn_3a']:+.1f} %" if pd.notna(metrics["cagr_rn_3a"]) else "N/A")
        f_cols[3].metric("Free Cash Flow (FCF)", f"{metrics['fcf']/1e6:,.1f} MMAD" if pd.notna(metrics["fcf"]) else "N/A")

        hist_chart = pd.DataFrame({
            "Exercice": ["N-3", "N-1", "N"],
            "Chiffre d'affaires (MMAD)": [row.get("ca_n3", 0)/1e6, row.get("ca_n1", 0)/1e6, row.get("ca_n", 0)/1e6],
            "Résultat Net (MMAD)": [row.get("resultat_net_n3", 0)/1e6, row.get("resultat_net_n1", 0)/1e6, row.get("resultat_net_n", 0)/1e6],
        })
        st.plotly_chart(px.bar(hist_chart, x="Exercice", y=["Chiffre d'affaires (MMAD)", "Résultat Net (MMAD)"], barmode="group", title="Trajectoire Historique CA & Résultat Net", color_discrete_sequence=["#172554", "#00BF63"]), use_container_width=True)
    else:
        st.info("Données comptables non encore saisies pour cette société dans `data/fondamentaux.csv`.")

elif active_page == "3. Valuation Multiples":
    st.subheader("Multiples de Valorisation (Cliquables)")
    render_clickable_indicators(["per", "peg", "pbr", "pfcf", "ev_ebitda"])
    if metrics["has_fundamentals"]:
        comp_m = pd.DataFrame({
            "Multiple": ["PER", "P/B", "P/FCF", "EV/EBITDA"],
            row["ticker"]: [metrics["per"], metrics["pbr"], metrics["pfcf"], metrics["ev_ebitda"]],
            f"Médiane {row['secteur_aff']}": [sec_med.get("per"), sec_med.get("pbr"), sec_med.get("pfcf"), sec_med.get("ev_ebitda")]
        })
        st.plotly_chart(px.bar(comp_m, x="Multiple", y=[row["ticker"], f"Médiane {row['secteur_aff']}"], barmode="group", title="Comparaison vs Médiane Sectorielle BVC", color_discrete_sequence=["#FF5310", "#172554"]), use_container_width=True)

elif active_page == "4. Dividend Analysis":
    st.subheader("Politique de Distribution & Soutenabilité")
    render_clickable_indicators(["rendement_div", "payout"])
    if metrics["has_fundamentals"]:
        c1, c2 = st.columns(2)
        c1.metric("Dividende par Action (DPA)", f"{row.get('dpa', 0):.2f} MAD")
        c2.metric("Couverture du Dividende", f"{metrics['couverture_div']:.2f}x" if pd.notna(metrics["couverture_div"]) else "N/A")
        hist_str = str(row.get("dpa_hist_5a", ""))
        if "|" in hist_str:
            vals_d = [float(x) for x in hist_str.split("|")]
            df_d = pd.DataFrame({"Année": ["N-4", "N-3", "N-2", "N-1", "N"], "DPA (MAD)": vals_d})
            st.plotly_chart(px.bar(df_d, x="Année", y="DPA (MAD)", title="Historique des Dividendes sur 5 ans (MAD)", color_discrete_sequence=["#00BF63"]), use_container_width=True)

elif active_page == "5. Financial Structure":
    st.subheader("Structure Bilancielle & Solvabilité")
    if metrics["est_financiere"]:
        st.info("Société du secteur financier (Banque / Assurance) : les ratios Dette Nette / EBITDA et Liquidité Générale ne sont pas pertinents. Analysez le ratio de levier Capitaux Propres / Total Actif.")
        if metrics["has_fundamentals"]:
            lev = (row["capitaux_propres"] / row["total_actif"]) * 100
            st.metric("Ratio Capitaux Propres / Total Actif", f"{lev:.2f} %")
    else:
        render_clickable_indicators(["dette_nette_ebitda", "liquidite_generale"])
        if metrics["has_fundamentals"]:
            c1, c2, c3 = st.columns(3)
            c1.metric("Enterprise Value (EV)", f"{metrics['ev']/1e6:,.0f} MMAD" if pd.notna(metrics["ev"]) else "N/A")
            c2.metric("Dette Financière Nette", f"{metrics['dette_nette']/1e6:,.0f} MMAD" if pd.notna(metrics["dette_nette"]) else "N/A")
            c3.metric("Couverture des Intérêts (EBIT/Int.)", f"{metrics['couverture_interets']:.1f}x" if pd.notna(metrics["couverture_interets"]) else "N/A")

elif active_page == "6. Intrinsic Valuation":
    st.subheader("Calculateur Interactif de Valorisation Intrinsèque (DCF FCFF & FCFE / Modèle Banques)")
    if not metrics["has_fundamentals"]:
        st.warning("Données fondamentales requises dans `data/fondamentaux.csv` pour exécuter le modèle DCF.")
    else:
        p1, p2, p3, p4 = st.columns(4)
        g_ca_in = p1.slider("Croissance CA (%)", -5.0, 25.0, float(default_dcf_params["g_ca"]), 0.5)
        m_ebit_in = p2.slider("Marge Opérationnelle EBIT (%)", 2.0, 55.0, float(default_dcf_params["marge_ebit"]), 0.5)
        capex_in = p3.slider("CAPEX (% du CA)", 1.0, 30.0, float(default_dcf_params["capex_pct"]), 0.5)
        g_term_in = p4.slider("Croissance Terminale g (%)", 1.0, 4.5, 2.5, 0.25)

        q1, q2, q3, q4 = st.columns(4)
        rf_in = q1.number_input("Taux sans risque Maroc (%)", 2.0, 8.0, 3.5, 0.25)
        erp_in = q2.number_input("Prime de risque marché (%)", 4.0, 12.0, 6.5, 0.25)
        kd_in = q3.number_input("Coût de la dette Kd (%)", 2.0, 12.0, 5.0, 0.25)
        hor_in = q4.selectbox("Horizon (années)", [5, 7, 10], index=0)

        custom_params = {
            "rf": rf_in, "erp": erp_in, "kd": kd_in, "tax": 32.0,
            "g_ca": g_ca_in, "marge_ebit": m_ebit_in, "capex_pct": capex_in,
            "bfr_pct": 1.5, "g_term": g_term_in, "horizon": hor_in
        }
        dcf_live = run_dcf_model(row, metrics, custom_params)

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("WACC / Coût Fonds Propres", f"{dcf_live['wacc']:.2f} %")
        r2.metric("Valeur Intrinsèque (FCFF / P-B)", f"{dcf_live['vi_fcff']:.2f} MAD" if pd.notna(dcf_live["vi_fcff"]) else "N/A")
        r3.metric("Valeur Intrinsèque (FCFE / DDM)", f"{dcf_live['vi_fcfe']:.2f} MAD" if pd.notna(dcf_live["vi_fcfe"]) else "N/A")
        r4.metric("Upside & Marge de Sécurité", f"{dcf_live['upside']:+.1f} %", f"MoS : {dcf_live['marge_securite']:+.1f} %")

        if not dcf_live["projections"].empty:
            st.dataframe(dcf_live["projections"].style.format("{:.2f}", subset=dcf_live["projections"].columns[1:]), use_container_width=True, hide_index=True)

elif active_page == "7. Comparative Valuation":
    st.subheader("Football Field Valuation — Synthèse des Méthodes")
    if not metrics["has_fundamentals"]:
        st.warning("Données fondamentales insuffisantes pour construire le Football Field.")
    else:
        methods = []
        if dcf_res.get("valid") and pd.notna(dcf_res["vi_action"]):
            vi = dcf_res["vi_action"]
            methods.append(("DCF / Modèle Intrinsèque", vi * 0.88, vi, vi * 1.12))
        if pd.notna(metrics["bpa"]) and metrics["bpa"] > 0:
            med_p = sec_med.get("per", 16.0) or 16.0
            methods.append(("Multiple PER Sectoriel", metrics["bpa"] * med_p * 0.85, metrics["bpa"] * med_p, metrics["bpa"] * med_p * 1.15))
        if pd.notna(metrics["vcpa"]) and metrics["vcpa"] > 0:
            med_pb = sec_med.get("pbr", 2.0) or 2.0
            methods.append(("Multiple P/B Sectoriel", metrics["vcpa"] * med_pb * 0.85, metrics["vcpa"] * med_pb, metrics["vcpa"] * med_pb * 1.15))

        if methods:
            fig_ff = go.Figure()
            for m_name, low, mid, high in methods:
                fig_ff.add_trace(go.Bar(
                    y=[m_name], x=[high - low], base=[low], orientation="h",
                    marker_color="#4E4C9B", name=m_name,
                    text=[f"{low:.1f} - {high:.1f} MAD (Central: {mid:.1f})"], textposition="inside"
                ))
            fig_ff.add_vline(x=row["cours"], line_dash="dash", line_color="#FF5310", annotation_text=f"Cours actuel : {row['cours']:.2f} MAD")
            fig_ff.update_layout(title="Football Field Valuation (Fourchettes en MAD)", showlegend=False, xaxis_title="Valeur par action (MAD)")
            st.plotly_chart(fig_ff, use_container_width=True)

elif active_page == "8. Scenarios & Sensitivity Analysis":
    st.subheader("Scénarios Bear / Base / Bull & Matrice de Sensibilité")
    if not metrics["has_fundamentals"]:
        st.warning("Données fondamentales requises.")
    else:
        scen_specs = {
            "Bear Case (Prudent)": {**default_dcf_params, "g_ca": default_dcf_params["g_ca"] - 3.0, "marge_ebit": max(default_dcf_params["marge_ebit"] - 2.5, 2.0), "rf": 4.25, "g_term": 1.75},
            "Base Case (Central)": default_dcf_params,
            "Bull Case (Optimiste)": {**default_dcf_params, "g_ca": default_dcf_params["g_ca"] + 3.0, "marge_ebit": default_dcf_params["marge_ebit"] + 2.0, "rf": 3.0, "g_term": 3.0},
        }
        s_rows = []
        for s_name, s_p in scen_specs.items():
            res_s = run_dcf_model(row, metrics, s_p)
            s_rows.append({
                "Scénario": s_name,
                "WACC / Ke (%)": f"{res_s['wacc']:.2f}%",
                "Valeur Intrinsèque (MAD)": f"{res_s['vi_action']:.2f}" if pd.notna(res_s["vi_action"]) else "N/A",
                "Upside / Downside": f"{res_s['upside']:+.1f}%" if pd.notna(res_s["upside"]) else "N/A",
                "Marge de Sécurité": f"{res_s['marge_securite']:+.1f}%" if pd.notna(res_s["marge_securite"]) else "N/A",
            })
        st.dataframe(pd.DataFrame(s_rows), use_container_width=True, hide_index=True)

        # Matrice de sensibilité WACC / g
        if dcf_res.get("mode") == "DCF_CLASSIQUE":
            st.markdown("#### Matrice de Sensibilité DCF : WACC vs Croissance Terminale (g)")
            w_vals = [dcf_res["wacc"] - 1.0, dcf_res["wacc"] - 0.5, dcf_res["wacc"], dcf_res["wacc"] + 0.5, dcf_res["wacc"] + 1.0]
            g_vals = [1.5, 2.0, 2.5, 3.0, 3.5]
            mat = []
            for w_v in w_vals:
                r_mat = {}
                for g_v in g_vals:
                    p_tmp = {**default_dcf_params, "rf": default_dcf_params["rf"] + (w_v - dcf_res["wacc"]), "g_term": g_v}
                    v_tmp = run_dcf_model(row, metrics, p_tmp)["vi_action"]
                    r_mat[f"g = {g_v:.1f}%"] = round(v_tmp, 2) if pd.notna(v_tmp) else np.nan
                mat.append(r_mat)
            df_mat = pd.DataFrame(mat, index=[f"WACC {w:.2f}%" for w in w_vals])
            st.dataframe(df_mat, use_container_width=True)

elif active_page == "9. Investment Decision":
    st.subheader("SAHM FINAL INVESTMENT ANALYSIS")
    c1, c2, c3 = st.columns(3)
    c1.metric("Fundamental Score (Qualité)", f"{scores['fundamental_score']}/100" if scores["fundamental_score"] else "Données insuffisantes")
    c2.metric("Valuation Signal (Prix)", f"{scores['valuation_score']}/100" if scores["valuation_score"] else "Données insuffisantes")
    c3.metric("Conclusion SAHM", scores["conclusion_cat"])

    if scores["dimensions"]:
        dim_df = pd.DataFrame({"Dimension": list(scores["dimensions"].keys()), "Score (/100)": list(scores["dimensions"].values())})
        st.plotly_chart(px.bar(dim_df, x="Score (/100)", y="Dimension", orientation="h", range_x=[0, 100], title="Décomposition du SAHM Investment Score", color_discrete_sequence=["#00BF63"]), use_container_width=True)

    col_s, col_r = st.columns(2)
    with col_s:
        st.success("**Points Forts (Key Strengths)**\n\n" + "\n".join([f"- {s}" for s in scores["strengths"]]))
    with col_r:
        st.error("**Points Faibles & Risques (Key Risks)**\n\n" + "\n".join([f"- {w}" for w in scores["weaknesses"] + scores["alerts"]]))

    st.info(
        f"**Synthèse analytique SAHM ({row['societe_aff']}) :** La société obtient un Fundamental Score de "
        f"**{scores['fundamental_score'] or 'N/A'}/100** et un signal de valorisation classé en catégorie **« {scores['conclusion_cat']} »**. "
        "Cette synthèse repose sur les derniers états financiers publiés et les cours de clôture de la Bourse de Casablanca. "
        "*Avertissement : cette analyse constitue un outil d'aide à la décision et non une recommandation personnalisée d'achat ou de vente.*"
    )

elif active_page == "10. Research Report":
    st.subheader("Génération du Rapport Equity Research PDF (SAHM)")
    st.write("Téléchargez le dossier complet d'analyse et de valorisation au format PDF incluant l'ensemble des multiples, le DCF, les chaînes de diagnostic et la conclusion SAHM.")
    pdf_bytes = generate_sahm_pdf(row, metrics, dcf_res, scores, chains)
    st.download_button(
        label=f"📥 Télécharger le Rapport PDF — {row['societe_aff']} ({row['ticker']})",
        data=pdf_bytes,
        file_name=f"SAHM_Equity_Research_{row['ticker']}.pdf",
        mime="application/pdf"
    )
