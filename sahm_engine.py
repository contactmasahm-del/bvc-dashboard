import numpy as np
import pandas as pd

def sdiv(num, den):
    if pd.isna(num) or pd.isna(den) or den == 0:
        return np.nan
    return float(num) / float(den)

def compute_company_metrics(row, sector_medians=None):
    cours = row.get("cours", np.nan)
    nb_act = row.get("nb_actions", np.nan)
    est_fin = bool(row.get("est_financiere", False)) or str(row.get("secteur", "")).lower() in [
        "banques", "assurances", "sociétés de financement", "banques & finance"
    ]

    # Vérification disponibilité des données fondamentales
    has_fd = pd.notna(row.get("resultat_net_n")) and pd.notna(nb_act) and nb_act > 0
    if not has_fd:
        return {
            "has_fundamentals": False,
            "est_financiere": est_fin,
            "capi": np.nan,
            "ev": np.nan,
            "dette_nette": np.nan,
            "bpa": np.nan,
            "vcpa": np.nan,
            "fcf": np.nan,
            "per": np.nan,
            "peg": np.nan,
            "pbr": np.nan,
            "pfcf": np.nan,
            "ev_ebitda": np.nan,
            "croissance_ca": np.nan,
            "croissance_rn": np.nan,
            "cagr_rn_3a": np.nan,
            "cagr_ca_3a": np.nan,
            "marge_nette": np.nan,
            "marge_ebitda": np.nan,
            "roe": np.nan,
            "roa": np.nan,
            "payout": np.nan,
            "rendement_div": np.nan,
            "couverture_div": np.nan,
            "dette_nette_ebitda": np.nan,
            "liquidite_generale": np.nan,
            "couverture_interets": np.nan,
        }

    capi = cours * nb_act
    rn_n = row.get("resultat_net_n", np.nan)
    rn_n1 = row.get("resultat_net_n1", np.nan)
    rn_n3 = row.get("resultat_net_n3", np.nan)
    ca_n = row.get("ca_n", np.nan)
    ca_n1 = row.get("ca_n1", np.nan)
    ca_n3 = row.get("ca_n3", np.nan)
    cp = row.get("capitaux_propres", np.nan)
    actif = row.get("total_actif", np.nan)
    ebitda = row.get("ebitda", np.nan)
    ebit = row.get("ebit", np.nan)
    dpa = row.get("dpa", 0.0)
    cfo = row.get("cfo", np.nan)
    capex = row.get("capex", np.nan)

    dette_fin = row.get("dette_financiere", 0.0) or 0.0
    treso = row.get("tresorerie", 0.0) or 0.0
    dette_nette = np.nan if est_fin else (dette_fin - treso)
    ev = np.nan if est_fin else (capi + dette_nette)

    bpa = sdiv(rn_n, nb_act)
    vcpa = sdiv(cp, nb_act)
    fcf = np.nan if est_fin else (cfo - capex if pd.notna(cfo) and pd.notna(capex) else np.nan)

    croissance_rn = ((rn_n / rn_n1) - 1) * 100 if pd.notna(rn_n) and pd.notna(rn_n1) and rn_n1 > 0 else np.nan
    croissance_ca = ((ca_n / ca_n1) - 1) * 100 if pd.notna(ca_n) and pd.notna(ca_n1) and ca_n1 > 0 else np.nan
    cagr_rn_3a = (((rn_n / rn_n3) ** (1 / 3)) - 1) * 100 if pd.notna(rn_n) and pd.notna(rn_n3) and rn_n > 0 and rn_n3 > 0 else np.nan
    cagr_ca_3a = (((ca_n / ca_n3) ** (1 / 3)) - 1) * 100 if pd.notna(ca_n) and pd.notna(ca_n3) and ca_n > 0 and ca_n3 > 0 else np.nan

    per = sdiv(cours, bpa) if pd.notna(bpa) and bpa > 0 else np.nan
    peg = sdiv(per, croissance_rn) if pd.notna(per) and pd.notna(croissance_rn) and croissance_rn > 0 else np.nan
    pbr = sdiv(capi, cp) if pd.notna(cp) and cp > 0 else np.nan
    pfcf = sdiv(capi, fcf) if (not est_fin) and pd.notna(fcf) and fcf > 0 else np.nan
    ev_ebitda = sdiv(ev, ebitda) if (not est_fin) and pd.notna(ebitda) and ebitda > 0 else np.nan

    marge_nette = sdiv(rn_n, ca_n) * 100 if pd.notna(ca_n) and ca_n > 0 else np.nan
    marge_ebitda = sdiv(ebitda, ca_n) * 100 if (not est_fin) and pd.notna(ebitda) and pd.notna(ca_n) and ca_n > 0 else np.nan
    roe = sdiv(rn_n, cp) * 100 if pd.notna(cp) and cp > 0 else np.nan
    roa = sdiv(rn_n, actif) * 100 if pd.notna(actif) and actif > 0 else np.nan

    div_total = (dpa or 0.0) * nb_act
    payout = sdiv(div_total, rn_n) * 100 if pd.notna(rn_n) and rn_n > 0 else np.nan
    rendement_div = sdiv(dpa, cours) * 100 if pd.notna(cours) and cours > 0 else np.nan
    couverture_div = sdiv(fcf, div_total) if (not est_fin) and pd.notna(fcf) and div_total > 0 else (
        sdiv(rn_n, div_total) if est_fin and div_total > 0 else np.nan
    )

    dette_nette_ebitda = sdiv(dette_nette, ebitda) if (not est_fin) and pd.notna(ebitda) and ebitda > 0 else np.nan
    liquidite_generale = sdiv(row.get("actifs_courants"), row.get("passifs_courants")) if not est_fin else np.nan
    couverture_interets = sdiv(ebit, row.get("charges_financieres")) if (not est_fin) and pd.notna(row.get("charges_financieres")) and row.get("charges_financieres") > 0 else np.nan

    return {
        "has_fundamentals": True,
        "est_financiere": est_fin,
        "capi": capi,
        "ev": ev,
        "dette_nette": dette_nette,
        "bpa": bpa,
        "vcpa": vcpa,
        "fcf": fcf,
        "per": per,
        "peg": peg,
        "pbr": pbr,
        "pfcf": pfcf,
        "ev_ebitda": ev_ebitda,
        "croissance_ca": croissance_ca,
        "croissance_rn": croissance_rn,
        "cagr_rn_3a": cagr_rn_3a,
        "cagr_ca_3a": cagr_ca_3a,
        "marge_nette": marge_nette,
        "marge_ebitda": marge_ebitda,
        "roe": roe,
        "roa": roa,
        "payout": payout,
        "rendement_div": rendement_div,
        "couverture_div": couverture_div,
        "dette_nette_ebitda": dette_nette_ebitda,
        "liquidite_generale": liquidite_generale,
        "couverture_interets": couverture_interets,
    }

def run_dcf_model(row, metrics, params):
    """
    Calcule le WACC, le DCF FCFF, le DCF FCFE, et pour les banques le modèle P/B-ROE / DDM.
    """
    if not metrics["has_fundamentals"]:
        return {"valid": False, "reason": "Données fondamentales insuffisantes"}

    cours = row["cours"]
    nb_act = row["nb_actions"]
    rf = params["rf"] / 100.0
    erp = params["erp"] / 100.0
    beta = row.get("beta", 1.0) if pd.notna(row.get("beta")) else 1.0
    ke = rf + beta * erp
    g_term = params["g_term"] / 100.0
    horizon = int(params["horizon"])

    # Méthodologie spécifique Banques & Assurances (P/B justifié par ROE + DDM)
    if metrics["est_financiere"]:
        roe_dec = (metrics["roe"] or 10.0) / 100.0
        g_div = min(params["g_ca"] / 100.0, ke - 0.015)
        dpa = row.get("dpa", 0.0) or 0.0
        ddm_val = (dpa * (1 + g_div)) / max(ke - g_div, 0.015) if dpa > 0 else np.nan
        justified_pb = max((roe_dec - g_term) / max(ke - g_term, 0.015), 0.3)
        pb_roe_val = justified_pb * metrics["vcpa"]
        vals = [v for v in [ddm_val, pb_roe_val] if pd.notna(v) and v > 0]
        vi_action = float(np.mean(vals)) if vals else np.nan
        mos = ((vi_action - cours) / vi_action * 100) if pd.notna(vi_action) and vi_action > 0 else np.nan
        upside = ((vi_action / cours) - 1) * 100 if pd.notna(vi_action) and cours > 0 else np.nan
        return {
            "valid": True,
            "mode": "BANQUE_DDM_PB_ROE",
            "ke": ke * 100,
            "kd_net": np.nan,
            "wacc": ke * 100,
            "vi_fcff": pb_roe_val,
            "vi_fcfe": ddm_val,
            "vi_action": vi_action,
            "marge_securite": mos,
            "upside": upside,
            "projections": pd.DataFrame(),
        }

    # Entreprise non financière : WACC + DCF FCFF + DCF FCFE
    kd = params["kd"] / 100.0
    tax = params["tax"] / 100.0
    capi = metrics["capi"]
    dette = max(row.get("dette_financiere", 0.0) or 0.0, 0.0)
    total_cap = capi + dette
    w_e = capi / total_cap if total_cap > 0 else 1.0
    w_d = dette / total_cap if total_cap > 0 else 0.0
    wacc = (ke * w_e) + (kd * (1 - tax) * w_d)
    wacc = max(wacc, g_term + 0.015)

    ca_base = row.get("ca_n", 0.0) or 0.0
    g_ca = params["g_ca"] / 100.0
    marge_ebit = params["marge_ebit"] / 100.0
    capex_pct = params["capex_pct"] / 100.0
    bfr_pct = params["bfr_pct"] / 100.0

    proj_rows = []
    pv_fcff_sum = 0.0
    pv_fcfe_sum = 0.0
    ca_prev = ca_base
    charges_fin = row.get("charges_financieres", 0.0) or 0.0

    for yr in range(1, horizon + 1):
        ca_t = ca_prev * (1 + g_ca)
        delta_ca = ca_t - ca_prev
        ebit_t = ca_t * marge_ebit
        nopat_t = ebit_t * (1 - tax)
        # Approximation amortissements ~ 75% du CAPEX de maintenance
        da_t = ca_t * (capex_pct * 0.75)
        capex_t = ca_t * capex_pct
        delta_bfr_t = delta_ca * bfr_pct
        fcff_t = nopat_t + da_t - capex_t - delta_bfr_t
        fcfe_t = fcff_t - charges_fin * (1 - tax)

        df_wacc = (1 + wacc) ** yr
        df_ke = (1 + max(ke, g_term + 0.015)) ** yr
        pv_fcff = fcff_t / df_wacc
        pv_fcfe = fcfe_t / df_ke
        pv_fcff_sum += pv_fcff
        pv_fcfe_sum += pv_fcfe

        proj_rows.append({
            "Année": f"N+{yr}",
            "CA (MMAD)": ca_t / 1e6,
            "EBIT (MMAD)": ebit_t / 1e6,
            "FCFF (MMAD)": fcff_t / 1e6,
            "FCFE (MMAD)": fcfe_t / 1e6,
            "FCFF Actualisé (MMAD)": pv_fcff / 1e6,
        })
        ca_prev = ca_t

    fcff_term = (proj_rows[-1]["FCFF (MMAD)"] * 1e6) * (1 + g_term)
    vt_fcff = fcff_term / (wacc - g_term)
    pv_vt_fcff = vt_fcff / ((1 + wacc) ** horizon)
    ev_dcf = pv_fcff_sum + pv_vt_fcff
    eq_fcff = ev_dcf - (metrics["dette_nette"] or 0.0)
    vi_fcff = max(eq_fcff / nb_act, 0.0)

    ke_eff = max(ke, g_term + 0.015)
    fcfe_term = (proj_rows[-1]["FCFE (MMAD)"] * 1e6) * (1 + g_term)
    vt_fcfe = fcfe_term / (ke_eff - g_term)
    pv_vt_fcfe = vt_fcfe / ((1 + ke_eff) ** horizon)
    vi_fcfe = max((pv_fcfe_sum + pv_vt_fcfe) / nb_act, 0.0)

    vi_action = vi_fcff
    mos = ((vi_action - cours) / vi_action * 100) if vi_action > 0 else np.nan
    upside = ((vi_action / cours) - 1) * 100 if cours > 0 else np.nan

    return {
        "valid": True,
        "mode": "DCF_CLASSIQUE",
        "ke": ke * 100,
        "kd_net": kd * (1 - tax) * 100,
        "wacc": wacc * 100,
        "vi_fcff": vi_fcff,
        "vi_fcfe": vi_fcfe,
        "vi_action": vi_action,
        "marge_securite": mos,
        "upside": upside,
        "projections": pd.DataFrame(proj_rows),
    }

def compute_sahm_scores(row, metrics, dcf_res, sector_medians):
    """
    Sépare obligatoirement :
    1) Fundamental Score (qualité financière : Rentabilité, Croissance, Santé financière, Dividendes)
    2) Valuation Signal (attractivité du cours actuel : Multiples vs secteur + Marge de sécurité DCF)
    """
    if not metrics["has_fundamentals"]:
        return {
            "status": "Données insuffisantes",
            "fundamental_score": None,
            "valuation_score": None,
            "global_score": None,
            "dimensions": {},
            "valuation_signal": "Données insuffisantes",
            "conclusion_cat": "Données insuffisantes",
            "strengths": [],
            "weaknesses": ["Données comptables manquantes dans fondamentaux.csv"],
            "alerts": ["Saisir les états financiers pour débloquer la notation complète."],
        }

    # 1. Rentabilité (sur 100)
    roe = metrics["roe"] or 0.0
    marge_n = metrics["marge_nette"] or 0.0
    s_rent = np.clip((roe / 20.0) * 60 + (marge_n / 20.0) * 40, 10, 100)

    # 2. Croissance (sur 100)
    g_rn = metrics["croissance_rn"] if pd.notna(metrics["croissance_rn"]) else 0.0
    g_ca = metrics["croissance_ca"] if pd.notna(metrics["croissance_ca"]) else 0.0
    s_croiss = np.clip(50 + (g_rn * 1.5) + (g_ca * 1.0), 10, 100)

    # 3. Santé financière (sur 100)
    if metrics["est_financiere"]:
        # Solvabilité proxifiée par levier Actif/Capitaux propres
        levier = sdiv(row.get("total_actif"), row.get("capitaux_propres")) or 10.0
        s_sante = np.clip(110 - (levier * 4.5), 20, 95)
    else:
        dn_ebitda = metrics["dette_nette_ebitda"] if pd.notna(metrics["dette_nette_ebitda"]) else 1.5
        liq = metrics["liquidite_generale"] if pd.notna(metrics["liquidite_generale"]) else 1.2
        s_sante = np.clip(80 - (dn_ebitda * 15) + ((liq - 1.0) * 20), 10, 100)

    # 4. Dividendes (sur 100)
    r_div = metrics["rendement_div"] or 0.0
    payout = metrics["payout"] if pd.notna(metrics["payout"]) else 50.0
    payout_bonus = 25 if 25 <= payout <= 80 else (10 if payout < 25 else 5)
    s_div = np.clip((r_div / 6.0) * 75 + payout_bonus, 10, 100)

    # Fundamental Score (pondération normalisée sur les 70 pts fondamentaux)
    fund_score = round((s_rent * 0.25 + s_croiss * 0.15 + s_sante * 0.20 + s_div * 0.10) / 0.70, 1)

    # 5. Valorisation (sur 100) — attractivité du prix
    val_parts = []
    if pd.notna(metrics["per"]) and metrics["per"] > 0:
        med_per = sector_medians.get("per", 16.0) or 16.0
        ratio_per = med_per / metrics["per"]
        val_parts.append(np.clip(ratio_per * 55, 10, 100))
    if pd.notna(metrics["pbr"]) and metrics["pbr"] > 0:
        med_pb = sector_medians.get("pbr", 2.0) or 2.0
        val_parts.append(np.clip((med_pb / metrics["pbr"]) * 55, 10, 100))
    if dcf_res.get("valid") and pd.notna(dcf_res.get("marge_securite")):
        mos = dcf_res["marge_securite"]
        val_parts.append(np.clip(50 + mos * 1.2, 5, 100))

    val_score = round(float(np.mean(val_parts)), 1) if val_parts else 50.0
    global_score = round(fund_score * 0.70 + val_score * 0.30, 1)

    if val_score >= 72:
        val_signal = "Sous-évaluée"
    elif val_score >= 58:
        val_signal = "Potentiellement sous-évaluée"
    elif val_score >= 42:
        val_signal = "Correctement valorisée"
    elif val_score >= 28:
        val_signal = "Potentiellement surévaluée"
    else:
        val_signal = "Surévaluée"

    strengths, weaknesses, alerts = [], [], []
    if roe >= 15:
        strengths.append(f"Rentabilité des capitaux propres élevée (ROE de {roe:.1f} %).")
    elif roe < 8:
        weaknesses.append(f"ROE modeste ({roe:.1f} %) inférieur au coût des fonds propres.")
    if g_rn > 10:
        strengths.append(f"Forte dynamique bénéficiaire (+{g_rn:.1f} % sur un an).")
    elif g_rn < 0:
        weaknesses.append(f"Contraction du résultat net ({g_rn:.1f} %).")
    if not metrics["est_financiere"] and pd.notna(metrics["dette_nette_ebitda"]):
        if metrics["dette_nette_ebitda"] <= 1.5:
            strengths.append(f"Structure bilancielle saine (Dette nette/EBITDA à {metrics['dette_nette_ebitda']:.2f}x).")
        elif metrics["dette_nette_ebitda"] > 3.0:
            weaknesses.append(f"Endettement élevé (Dette nette/EBITDA à {metrics['dette_nette_ebitda']:.2f}x).")
            alerts.append("Surveiller la capacité de désendettement et le coût de la dette.")
    if r_div >= 4.0:
        strengths.append(f"Rendement du dividende attractif ({r_div:.2f} %).")
    if pd.notna(metrics["payout"]) and metrics["payout"] > 95:
        alerts.append(f"Payout ratio très élevé ({metrics['payout']:.0f} %) : risque sur la pérennité du dividende.")

    return {
        "status": "Complet",
        "fundamental_score": fund_score,
        "valuation_score": val_score,
        "global_score": global_score,
        "dimensions": {
            "Valorisation (30%)": round(val_score, 1),
            "Rentabilité (25%)": round(s_rent, 1),
            "Croissance (15%)": round(s_croiss, 1),
            "Santé financière (20%)": round(s_sante, 1),
            "Dividendes (10%)": round(s_div, 1),
        },
        "valuation_signal": val_signal,
        "conclusion_cat": val_signal,
        "strengths": strengths or ["Profil opérationnel globalement équilibré."],
        "weaknesses": weaknesses or ["Aucun point faible majeur détecté sur les données disponibles."],
        "alerts": alerts,
    }
