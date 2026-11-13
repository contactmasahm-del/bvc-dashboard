from fpdf import FPDF
import pandas as pd

def clean_txt(text):
    if text is None:
        return "N/A"
    s = str(text)
    replacements = {
        "—": "-", "–": "-", "’": "'", "«": '"', "»": '"',
        "→": "->", "≤": "<=", "≥": ">=", "×": "x", "…": "..."
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")

def generate_sahm_pdf(row, metrics, dcf_res, scores, chains):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # En-tête SAHM Bleu Marine (#172554)
    pdf.set_fill_color(23, 37, 84)
    pdf.rect(0, 0, 210, 32, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_xy(12, 8)
    pdf.cell(0, 8, clean_txt("SAHM EQUITY RESEARCH - RAPPORT DE VALORISATION BVC"), ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_x(12)
    pdf.cell(0, 6, clean_txt(f"{row['societe_aff']} ({row['ticker']}) | Secteur : {row['secteur_aff']} | Cours : {row['cours']:.2f} MAD"), ln=True)

    pdf.ln(14)
    pdf.set_text_color(23, 37, 84)

    def section_title(num, title):
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_fill_color(241, 245, 249)
        pdf.set_text_color(23, 37, 84)
        pdf.cell(0, 7, clean_txt(f"  {num}. {title}"), ln=True, fill=True)
        pdf.set_text_color(30, 41, 59)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.ln(1)

    def fmt(val, suffix=""):
        return f"{val:.2f}{suffix}" if pd.notna(val) else "N/A"

    # 1. Présentation & 2. Synthèse exécutive
    section_title(1, "PRESENTATION DE LA SOCIETE & DONNEES DE MARCHE")
    pdf.multi_cell(0, 5, clean_txt(
        f"Société : {row['societe_aff']} ({row['ticker']}) | Secteur : {row['secteur_aff']}\n"
        f"Cours actuel : {row['cours']:.2f} MAD ({row.get('variation_pct', 0):+.2f}%) | "
        f"Capitalisation : {fmt(metrics['capi']/1e6 if pd.notna(metrics['capi']) else None, ' MMAD')}\n"
        f"Date de mise à jour : {row.get('date', 'N/A')} | Source : {row.get('source', 'Bourse de Casablanca')}"
    ))

    section_title(2, "SYNTHESE EXECUTIVE & SAHM INVESTMENT SCORE")
    pdf.multi_cell(0, 5, clean_txt(
        f"Diagnostic Global : {scores['conclusion_cat']}\n"
        f"Fundamental Score (Qualité) : {scores['fundamental_score'] or 'N/A'}/100 | "
        f"Valuation Signal Score (Prix) : {scores['valuation_score'] or 'N/A'}/100 | "
        f"Score Global : {scores['global_score'] or 'N/A'}/100"
    ))

    # 3, 4, 5, 6. Tableaux d'indicateurs
    section_title(3, "ANALYSE FONDAMENTALE, MULTIPLES, DIVIDENDES & STRUCTURE")
    lines = [
        f"Multiples : PER = {fmt(metrics['per'], 'x')} | PEG = {fmt(metrics['peg'], 'x')} | P/B = {fmt(metrics['pbr'], 'x')} | P/FCF = {fmt(metrics['pfcf'], 'x')} | EV/EBITDA = {fmt(metrics['ev_ebitda'], 'x')}",
        f"Performance : ROE = {fmt(metrics['roe'], '%')} | ROA = {fmt(metrics['roa'], '%')} | Marge Nette = {fmt(metrics['marge_nette'], '%')} | Croissance RN = {fmt(metrics['croissance_rn'], '%')}",
        f"Dividendes : Rendement = {fmt(metrics['rendement_div'], '%')} | Payout Ratio = {fmt(metrics['payout'], '%')} | Couverture = {fmt(metrics['couverture_div'], 'x')}",
        f"Structure : Dette Nette = {fmt(metrics['dette_nette']/1e6 if pd.notna(metrics['dette_nette']) else None, ' MMAD')} | Dette/EBITDA = {fmt(metrics['dette_nette_ebitda'], 'x')} | Liquidité = {fmt(metrics['liquidite_generale'], 'x')}",
    ]
    for l in lines:
        pdf.multi_cell(0, 5, clean_txt(l))

    section_title(4, "VALORISATION INTRINSEQUE (DCF / MODELE SECTORIEL)")
    if dcf_res.get("valid"):
        pdf.multi_cell(0, 5, clean_txt(
            f"Méthodologie : {dcf_res['mode']} | WACC / Ke : {fmt(dcf_res['wacc'], '%')}\n"
            f"Valeur Intrinsèque par action : {fmt(dcf_res['vi_action'], ' MAD')} | Cours actuel : {row['cours']:.2f} MAD\n"
            f"Upside / Downside potentiel : {fmt(dcf_res['upside'], '%')} | Marge de sécurité : {fmt(dcf_res['marge_securite'], '%')}"
        ))
    else:
        pdf.multi_cell(0, 5, clean_txt("Données insuffisantes pour exécuter le modèle DCF."))

    section_title(5, "CHAINES D'ANALYSE & DIAGNOSTIC DE COHERENCE")
    for ch in chains:
        pdf.multi_cell(0, 5, clean_txt(f"- {ch['titre']} [{ch['statut']}] : {ch['analyse']}"))

    section_title(6, "POINTS FORTS, RISQUES & CONCLUSION SAHM")
    pdf.multi_cell(0, 5, clean_txt(
        "Points forts : " + " ; ".join(scores["strengths"]) + "\n"
        "Points faibles & Risques : " + " ; ".join(scores["weaknesses"] + scores["alerts"]) + "\n\n"
        "Avertissement : Ce rapport est produit automatiquement par SAHM à titre éducatif et analytique. Il ne constitue pas un conseil en investissement personnalisé."
    ))

    return bytes(pdf.output())
