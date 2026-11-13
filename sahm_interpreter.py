import pandas as pd

INDICATOR_META = {
    "per": {
        "nom": "PER (Price Earnings Ratio)",
        "unit": "x",
        "formule": "PER = Cours de l'action / Bénéfice Net par Action (BPA)",
        "definition": "Nombre d'années de bénéfices nets actuels que l'investisseur accepte de payer pour acquérir une action.",
        "signification": "Mesure la cherté relative du titre par rapport à sa capacité bénéficiaire immédiate et reflète les anticipations de croissance du marché.",
        "lies": ["PEG", "Croissance du résultat net", "ROE", "P/B"],
        "vigilance": "Un PER faible ne garantit pas une bonne affaire : il peut traduire une baisse attendue des bénéfices ou un risque sectoriel élevé.",
    },
    "peg": {
        "nom": "PEG (Price/Earnings to Growth)",
        "unit": "x",
        "formule": "PEG = PER / Taux de croissance annuel du BPA (%)",
        "definition": "Relie le multiple de valorisation (PER) au rythme de croissance des bénéfices.",
        "signification": "Permet de vérifier si un PER élevé est justifié par une croissance rapide des résultats.",
        "lies": ["PER", "Croissance du résultat net", "CAGR 3 ans"],
        "vigilance": "Très sensible à la volatilité ponctuelle du résultat net sur un seul exercice.",
    },
    "pbr": {
        "nom": "P/B (Price to Book Ratio)",
        "unit": "x",
        "formule": "P/B = Capitalisation boursière / Capitaux propres",
        "definition": "Compare la valeur boursière de l'entreprise à sa valeur comptable nette (actif net).",
        "signification": "Particulièrement pertinent pour les banques et assurances où le bilan reflète directement la capacité de génération de revenus.",
        "lies": ["ROE", "ROA", "PER"],
        "vigilance": "Un P/B supérieur à 1x n'est justifié que si le ROE dépasse durablement le coût des fonds propres (Ke).",
    },
    "pfcf": {
        "nom": "P/FCF (Price to Free Cash Flow)",
        "unit": "x",
        "formule": "P/FCF = Capitalisation boursière / Free Cash Flow",
        "definition": "Mesure le multiple payé par le marché pour chaque dirham de trésorerie disponible après investissements.",
        "signification": "Plus fiable que le PER car le cash flow est moins sensible aux choix comptables que le résultat net.",
        "lies": ["FCF", "CAPEX", "Dette nette", "DCF"],
        "vigilance": "Peut être temporairement dégradé lors d'un cycle d'investissements (CAPEX) de croissance.",
    },
    "ev_ebitda": {
        "nom": "EV/EBITDA",
        "unit": "x",
        "formule": "EV/EBITDA = (Capitalisation + Dette nette) / EBITDA",
        "definition": "Compare la valeur totale de l'entreprise (actionnaires + créanciers) à son excédent brut d'exploitation.",
        "signification": "Permet de comparer des entreprises ayant des niveaux d'endettement et des politiques d'amortissement différents.",
        "lies": ["Enterprise Value", "Dette nette / EBITDA", "Marge EBITDA"],
        "vigilance": "Non pertinent pour les banques et assurances (structure bilancielle spécifique).",
    },
    "roe": {
        "nom": "ROE (Return on Equity)",
        "unit": "%",
        "formule": "ROE = Résultat net / Capitaux propres × 100",
        "definition": "Mesure le rendement financier généré pour les actionnaires sur les fonds propres investis.",
        "signification": "Indique l'efficacité avec laquelle la direction transforme les capitaux des actionnaires en profits.",
        "lies": ["ROA", "P/B", "Marge nette", "Dette nette / EBITDA"],
        "vigilance": "Un ROE élevé peut être artificiellement gonflé par un fort endettement (effet de levier). Vérifier le ROA en parallèle.",
    },
    "roa": {
        "nom": "ROA (Return on Assets)",
        "unit": "%",
        "formule": "ROA = Résultat net / Total Actif × 100",
        "definition": "Mesure la rentabilité économique dégagée par l'ensemble des actifs de l'entreprise.",
        "signification": "Évalue la performance opérationnelle pure indépendamment de la structure de financement.",
        "lies": ["ROE", "Marge nette", "Marge EBITDA"],
        "vigilance": "Les banques ont structurellement un ROA compris entre 0,8 % et 1,6 % en raison de la taille de leur bilan.",
    },
    "marge_nette": {
        "nom": "Marge Nette",
        "unit": "%",
        "formule": "Marge nette = Résultat net / Chiffre d'affaires × 100",
        "definition": "Part du chiffre d'affaires qui se transforme en bénéfice net final après toutes charges et impôts.",
        "signification": "Reflète le pouvoir de fixation des prix (pricing power) et la maîtrise des coûts.",
        "lies": ["Marge EBITDA", "ROE", "Croissance du résultat net"],
        "vigilance": "Peut intégrer des éléments exceptionnels non récurrents (cessions d'actifs, reprises de provisions).",
    },
    "rendement_div": {
        "nom": "Rendement du Dividende",
        "unit": "%",
        "formule": "Rendement = Dividende par action (DPA) / Cours actuel × 100",
        "definition": "Revenu annuel brut versé à l'actionnaire rapporté au prix d'achat de l'action.",
        "signification": "Mesure la rémunération immédiate du capital investi sur la Bourse de Casablanca.",
        "lies": ["Payout Ratio", "Couverture du dividende", "FCF"],
        "vigilance": "Un rendement anormalement élevé (> 8 %) peut signaler une chute récente du cours anticipant une baisse du futur dividende.",
    },
    "payout": {
        "nom": "Payout Ratio (Taux de distribution)",
        "unit": "%",
        "formule": "Payout = Dividendes distribués / Résultat net × 100",
        "definition": "Proportion des bénéfices annuels reversée aux actionnaires sous forme de dividendes.",
        "signification": "Évalue l'équilibre entre rémunération immédiate des actionnaires et autofinancement de la croissance.",
        "lies": ["Rendement du dividende", "Couverture du dividende", "ROE"],
        "vigilance": "Un payout supérieur à 100 % signifie que l'entreprise puise dans sa trésorerie ou s'endette pour payer son dividende.",
    },
    "dette_nette_ebitda": {
        "nom": "Dette Nette / EBITDA",
        "unit": "x",
        "formule": "Dette nette / EBITDA = (Dettes financières − Trésorerie) / EBITDA",
        "definition": "Nombre d'années d'excédent brut d'exploitation nécessaires pour rembourser intégralement la dette nette.",
        "signification": "Indicateur de référence de la solvabilité et de la capacité de désendettement.",
        "lies": ["Dette nette", "Couverture des intérêts", "FCF"],
        "vigilance": "Au-delà de 3,0x à 3,5x (hors concessions/infrastructures), le risque financier augmente sensiblement.",
    },
    "liquidite_generale": {
        "nom": "Liquidité Générale (Current Ratio)",
        "unit": "x",
        "formule": "Liquidité générale = Actifs courants / Passifs courants",
        "definition": "Capacité de l'entreprise à couvrir ses dettes à court terme avec ses actifs à moins d'un an.",
        "signification": "Mesure la sécurité de trésorerie à court terme.",
        "lies": ["Dette nette", "FCF", "Couverture des intérêts"],
        "vigilance": "Un ratio inférieur à 1,0x impose de surveiller la rotation des stocks et le besoin en fonds de roulement.",
    },
}

def inspect_indicator(key, value, row, metrics, sector_medians):
    meta = INDICATOR_META[key]
    sec_med = sector_medians.get(key)
    source = row.get("source", "Bourse de Casablanca / AMMC") if pd.notna(row.get("source")) else "Bourse de Casablanca"
    date_maj = row.get("date_maj", row.get("date", "N/A"))
    statut = row.get("statut_donnees", "Calculé") if pd.notna(row.get("statut_donnees")) else "Indisponible"

    if pd.isna(value):
        return {
            **meta,
            "valeur_str": "N/A (Donnée indisponible)",
            "diagnostic": "Données insuffisantes",
            "color": "#64748B",
            "interpretation": "Les données comptables nécessaires au calcul de cet indicateur ne sont pas encore disponibles ou ne s'appliquent pas à ce secteur.",
            "comp_secteur": "Non applicable",
            "comp_historique": "Historique en cours de constitution",
            "source": source,
            "date_maj": str(date_maj),
            "confiance": "Faible (donnée manquante)",
        }

    val_str = f"{value:.2f}{meta['unit']}"
    comp_sec_str = f"Médiane secteur : {sec_med:.2f}{meta['unit']}" if pd.notna(sec_med) else "Médiane secteur en cours de calcul"

    # Logique diagnostique contextualisée
    diag = "Neutre"
    color = "#FF5310"
    interp = ""

    if key == "per":
        ref = sec_med if pd.notna(sec_med) else 16.0
        interp = f"Le marché valorise actuellement l'entreprise à {value:.1f} fois son bénéfice annuel par action (contre {ref:.1f}x pour la médiane du secteur). "
        if value < ref * 0.85:
            diag, color = "Favorable", "#00BF63"
            interp += "Cette décote relative peut représenter une opportunité si les perspectives bénéficiaires restent solides."
        elif value > ref * 1.25:
            diag, color = "Vigilance", "#FF5310"
            interp += "Le titre se traite avec une prime importante qui exige une croissance soutenue des résultats pour être justifiée."
        else:
            diag, color = "Neutre", "#4E4C9B"
            interp += "Ce niveau est en ligne avec les standards de son secteur sur la Bourse de Casablanca."

    elif key == "roe":
        interp = f"L'entreprise génère {value:.1f} DH de résultat net pour chaque 100 DH de capitaux propres. "
        if value >= 15:
            diag, color = "Favorable", "#00BF63"
            interp += "Cette rentabilité financière est élevée et témoigne d'un avantage compétitif ou d'une excellente efficacité du capital."
        elif value >= 9:
            diag, color = "Neutre", "#4E4C9B"
            interp += "Cette rentabilité est satisfaisante, mais il convient de vérifier si elle couvre confortablement le coût des fonds propres."
        else:
            diag, color = "Défavorable", "#EF4444"
            interp += "Cette rentabilité des fonds propres est faible et pèse sur la création de valeur actionnariale."

    elif key == "dette_nette_ebitda":
        interp = f"Il faudrait {value:.2f} années d'EBITDA pour rembourser la dette financière nette. "
        if value <= 1.5:
            diag, color = "Favorable", "#00BF63"
            interp += "Le bilan est très solide et offre une marge de manœuvre confortable pour investir ou distribuer des dividendes."
        elif value <= 3.0:
            diag, color = "Neutre", "#4E4C9B"
            interp += "L'endettement reste maîtrisé mais doit être suivi au regard de la génération de Free Cash Flow."
        else:
            diag, color = "Défavorable", "#EF4444"
            interp += "Le levier financier est élevé et expose l'entreprise aux charges d'intérêts."

    elif key == "rendement_div":
        interp = f"Au cours actuel, l'action offre un rendement brut de {value:.2f} %. "
        if value >= 4.5:
            diag, color = "Favorable", "#00BF63"
            interp += "Ce rendement est attractif comparé aux placements sans risque sur le marché marocain."
        elif value >= 2.0:
            diag, color = "Neutre", "#4E4C9B"
            interp += "Rendement modéré, souvent associé à des valeurs privilégiant le réinvestissement de leurs bénéfices."
        else:
            diag, color = "Vigilance", "#FF5310"
            interp += "Faible distribution : l'attrait du titre repose principalement sur la plus-value en capital."

    else:
        interp = f"L'indicateur {meta['nom']} s'établit à {val_str}. Analysez-le conjointement avec ses indicateurs liés ({', '.join(meta['lies'][:3])}) pour valider la tendance."
        diag, color = "Neutre", "#4E4C9B"

    return {
        **meta,
        "valeur_str": val_str,
        "diagnostic": diag,
        "color": color,
        "interpretation": interp,
        "comp_secteur": comp_sec_str,
        "comp_historique": f"Comparé aux 3 derniers exercices ({row.get('periode', 'FY2025')})",
        "source": f"{source} ({statut})",
        "date_maj": str(date_maj),
        "confiance": "Élevée (données publiées)" if statut == "Réel" else "Modérée",
    }

def evaluate_analytical_chains(metrics, dcf_res):
    """
    Évalue les 5 chaînes d'analyse et détecte automatiquement les signaux contradictoires.
    """
    if not metrics["has_fundamentals"]:
        return [], []

    chains = [
        {
            "titre": "Chaîne 1 : Valorisation & Croissance (PER → PEG → Croissance RN → ROE)",
            "objectif": "Vérifier si le multiple payé en bourse est justifié par la croissance réelle.",
            "statut": "Cohérent" if (metrics["per"] or 99) < 20 and (metrics["croissance_rn"] or 0) > 5 else "Vigilance",
            "analyse": f"PER à {metrics['per']:.1f}x pour une croissance du résultat net de {metrics['croissance_rn']:.1f}% et un ROE de {metrics['roe']:.1f}%."
            if pd.notna(metrics["per"]) and pd.notna(metrics["croissance_rn"]) else "Données de croissance partielles.",
        },
        {
            "titre": "Chaîne 2 : Rentabilité Opérationnelle (ROE → ROA → Marge Nette → Marge EBITDA)",
            "objectif": "Distinguer la vraie performance économique de l'effet de levier financier.",
            "statut": "Solide" if (metrics["roe"] or 0) > 12 and (metrics["marge_nette"] or 0) > 8 else "À surveiller",
            "analyse": f"ROE de {metrics['roe']:.1f}% soutenu par une marge nette de {metrics['marge_nette']:.1f}% et un ROA de {metrics['roa']:.1f}%."
            if pd.notna(metrics["roe"]) and pd.notna(metrics["marge_nette"]) else "Rentabilité partiellement renseignée.",
        },
        {
            "titre": "Chaîne 3 : Endettement & Trésorerie (Dette Nette → EBITDA → FCF → Couverture Intérêts)",
            "objectif": "Évaluer la solvabilité et la capacité à générer du cash libre.",
            "statut": "Non applicable (Secteur Financier)" if metrics["est_financiere"] else (
                "Sain" if (metrics["dette_nette_ebitda"] or 0) < 2.5 else "Sous tension"
            ),
            "analyse": "Méthodologie prudentielle spécifique appliquée aux banques/assurances." if metrics["est_financiere"] else (
                f"Ratio Dette nette/EBITDA à {metrics['dette_nette_ebitda']:.2f}x avec un FCF de {(metrics['fcf']/1e6):.1f} MMAD."
                if pd.notna(metrics["dette_nette_ebitda"]) and pd.notna(metrics["fcf"]) else "Flux de trésorerie incomplets."
            ),
        },
        {
            "titre": "Chaîne 4 : Politique de Dividendes (Payout → Rendement → FCF → Couverture Dividende)",
            "objectif": "Vérifier que le dividende versé est couvert par les flux réels.",
            "statut": "Durable" if (metrics["payout"] or 100) <= 85 and (metrics["couverture_div"] or 0) >= 1.1 else "Vigilance",
            "analyse": f"Rendement de {metrics['rendement_div']:.2f}% avec un Payout de {metrics['payout']:.0f}% et une couverture de {metrics['couverture_div']:.2f}x."
            if pd.notna(metrics["payout"]) and pd.notna(metrics["couverture_div"]) else "Distribution à confirmer.",
        },
        {
            "titre": "Chaîne 5 : Valorisation Intrinsèque (FCF → WACC → g → DCF → Marge de Sécurité)",
            "objectif": "Comparer la valeur fondamentale intrinsèque au cours boursier actuel.",
            "statut": "Opportunité" if (dcf_res.get("marge_securite") or -99) > 10 else "Prime de marché",
            "analyse": f"Valeur intrinsèque estimée à {dcf_res['vi_action']:.2f} MAD (WACC {dcf_res['wacc']:.2f}%), soit une marge de sécurité de {dcf_res['marge_securite']:+.1f}%."
            if dcf_res.get("valid") and pd.notna(dcf_res.get("vi_action")) else "Modèle DCF indisponible.",
        },
    ]

    contradictions = []
    if pd.notna(metrics["roe"]) and pd.notna(metrics["roa"]) and metrics["roe"] > 18 and metrics["roa"] < 3 and not metrics["est_financiere"]:
        contradictions.append("Contradiction Rentabilité / Levier : ROE très élevé (>18%) mais ROA faible (<3%), indiquant que la rentabilité provient fortement de l'endettement.")
    if pd.notna(metrics["rendement_div"]) and pd.notna(metrics["payout"]) and metrics["rendement_div"] > 5 and metrics["payout"] > 95:
        contradictions.append("Contradiction Dividende : Rendement attractif (>5%) mais Payout >95% fragilisant la pérennité de la distribution.")
    if pd.notna(metrics["per"]) and pd.notna(metrics["croissance_rn"]) and metrics["per"] < 12 and metrics["croissance_rn"] < 0:
        contradictions.append("Contradiction Valorisation : PER faible (<12x) mais bénéfices en baisse : risque de 'Value Trap' (décote justifiée).")

    return chains, contradictions
