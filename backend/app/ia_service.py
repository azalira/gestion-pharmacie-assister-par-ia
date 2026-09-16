"""Service de recommandation IA - Gestion Pharmacie IA.

Architecture :
  Symptomes utilisateur
      |
  Analyse semantique (tokens + mots-cles medicaux)
      |
  Maladies probables
      |
  Base de connaissances symptomes -> medicaments indiques
      |
  Filtres : allergies, stock, contre-indications
      |
  Recommandations avec justification
      |
  Avertissement legal
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "ia"))

import symptomes_db

try:
    from rag.retriever import rechercher as rag_rechercher
    RAG_DISPONIBLE = True
except Exception:
    RAG_DISPONIBLE = False


# ── Helpers textuels ──────────────────────────────────────────────────────────

def _normaliser(texte):
    if not texte:
        return ""
    texte = texte.lower().strip()
    replacements = {
        "a": "a", "a": "a", "a": "a", "a": "a",
        "e": "e", "e": "e", "e": "e", "e": "e",
        "i": "i", "i": "i",
        "o": "o", "o": "o",
        "u": "u", "u": "u", "u": "u",
        "c": "c",
        "-": " ", "'": " ",
    }
    replacements = {
        "\u00e0": "a", "\u00e2": "a", "\u00e4": "a",
        "\u00e9": "e", "\u00e8": "e", "\u00ea": "e", "\u00eb": "e",
        "\u00ee": "i", "\u00ef": "i",
        "\u00f4": "o", "\u00f6": "o",
        "\u00f9": "u", "\u00fb": "u", "\u00fc": "u",
        "\u00e7": "c",
    }
    for src, dst in replacements.items():
        texte = texte.replace(src, dst)
    for ch in ["-", "'"]:
        texte = texte.replace(ch, " ")
    while "  " in texte:
        texte = texte.replace("  ", " ")
    return texte.strip()


def _tokens(texte):
    return {w for w in _normaliser(texte).split() if len(w) >= 2}


def _score_tokens(query_tokens, keyword_tokens):
    if not keyword_tokens:
        return 0.0
    overlap = query_tokens & keyword_tokens
    central = 0.1 if (query_tokens and (list(query_tokens)[-1] in keyword_tokens)) else 0.0
    return min(1.0, len(overlap) / len(keyword_tokens) + central)


# ── Base des maladies probables ────────────────────────────────────────────────

MALADIES = [
    {
        "maladie": "Grippe / Rhume",
        "symptomes": ["fievre", "courbature", "fatigue", "toux", "rhume", "grippe", "nez bouche", "mal de gorge", "frisson"],
        "probabilite": 0.82,
    },
    {
        "maladie": "Cephalee / Migraine",
        "symptomes": ["maux de tete", "mal a la tete", "mal de tete", "maux de crane", "cephalee", "migraine", "mal de crane"],
        "probabilite": 0.75,
    },
    {
        "maladie": "Angine / Pharyngite",
        "symptomes": ["mal de gorge", "gorge", "angine", "amygdale", "deglutition", "douleur gorge"],
        "probabilite": 0.72,
    },
    {
        "maladie": "Reflux gastro-oesophagien",
        "symptomes": ["brulure d estomac", "brulure estomac", "reflux", "remontee acide", "acidite", "pyrosis"],
        "probabilite": 0.70,
    },
    {
        "maladie": "Gastro-enterite",
        "symptomes": ["diarrhee", "mal au ventre", "vomissement", "nausee", "gastro", "ventre", "ballonnement abdominal"],
        "probabilite": 0.68,
    },
    {
        "maladie": "Allergie / Rhinite allergique",
        "symptomes": ["allergie", "rhinite", "nez qui coule", "urticaire", "demangeaison", "demangeaisons", "eczema"],
        "probabilite": 0.66,
    },
    {
        "maladie": "Asthme / Bronchospasme",
        "symptomes": ["asthme", "essoufflement", "sifflement respiratoire", "bronchospasme", "difficultes respiratoires"],
        "probabilite": 0.64,
    },
    {
        "maladie": "Infection bacterienne",
        "symptomes": ["infection", "fievre haute", "otite", "sinusite", "pneumonie", "bronchite", "cystite"],
        "probabilite": 0.62,
    },
    {
        "maladie": "Hypertension",
        "symptomes": ["tension elevee", "hypertension", "mal de tete nuque", "saignement de nez", "vertige"],
        "probabilite": 0.58,
    },
    {
        "maladie": "Constipation",
        "symptomes": ["constipation", "transit lent", "difficultes a defecation", "selles dures"],
        "probabilite": 0.55,
    },
    {
        "maladie": "Douleur articulaire / Arthralgie",
        "symptomes": ["douleur articulaire", "arthralgie", "articulation gonflee", "raideur articulaire", "arthrite"],
        "probabilite": 0.60,
    },
    {
        "maladie": "Insomnie / Troubles du sommeil",
        "symptomes": ["insomnie", "difficultes a dormir", "troubles du sommeil", "reveil nocturne"],
        "probabilite": 0.50,
    },
    {
        "maladie": "Anxiete / Stress",
        "symptomes": ["anxiete", "stress", "angoisse", "palpitations", "nervosite"],
        "probabilite": 0.55,
    },
]

# Classes therapeutiques par maladie (pour filtrage medical)
CLASSE_PAR_MALADIE = {
    "Grippe / Rhume": ["Antigrippe", "Antalgique", "AINS", "Antipyretique"],
    "Cephalee / Migraine": ["Antalgique", "AINS"],
    "Angine / Pharyngite": ["Antalgique", "AINS"],
    "Reflux gastro-oesophagien": ["Gastro-protecteur", "IPP"],
    "Gastro-enterite": ["Antidiarrheique", "Antispasmodique"],
    "Allergie / Rhinite allergique": ["Antihistaminique", "Corticoide"],
    "Asthme / Bronchospasme": ["Bronchodilatateur", "Corticoide"],
    "Infection bacterienne": ["Antibiotique"],
    "Hypertension": ["Antihypertenseur", "Diuretique"],
    "Constipation": ["Laxatif"],
    "Douleur articulaire / Arthralgie": ["AINS", "Antalgique"],
    "Insomnie / Troubles du sommeil": ["Anxiolytique"],
    "Anxiete / Stress": ["Anxiolytique"],
}

# Prix par classe (Ariary)
PRIX_PAR_CLASSE = {
    "antalgique": 1500.0,
    "antipyretique": 1500.0,
    "ains": 2000.0,
    "antiagregant": 1200.0,
    "antispasmodique": 2500.0,
    "gastro-protecteur": 3000.0,
    "antidiarrheique": 3200.0,
    "antifongique": 2800.0,
    "antibiotique": 5000.0,
    "corticoide": 4000.0,
    "antihistaminique": 2700.0,
    "antigrippe": 3000.0,
    "bronchodilatateur": 4500.0,
    "anxiolytique": 2600.0,
    "laxatif": 2600.0,
    "decongestionnant": 2500.0,
    "antiseptique": 1800.0,
    "veinotonique": 2800.0,
    "anticoagulant": 5500.0,
    "statine": 4200.0,
    "antihypertenseur": 3600.0,
    "diuretique": 2400.0,
    "hormone": 2200.0,
    "antidiabetique": 3800.0,
}


def _prix_par_classe(classe):
    cls = _normaliser(classe)
    for nom, prix in PRIX_PAR_CLASSE.items():
        if nom in cls:
            return prix
    return 3000.0


# ── Algorithme principal ───────────────────────────────────────────────────────

def recommander(symptomes, age=None, allergies=None):
    symptomes = (symptomes or "").strip()
    if not symptomes:
        raise ValueError("symptomes vide")

    qt = _tokens(symptomes)
    STOPWORDS = {
        "jai", "je", "tu", "il", "elle", "nous", "vous",
        "depuis", "quand", "quel", "quelle", "quest", "que", "qui", "quoi",
        "ca", "cela", "ce", "cet", "cette", "avec", "sans", "pour",
        "dans", "sur", "sous", "chez", "avant", "apres", "entre",
        "et", "ou", "donc", "mais", "car", "tres", "beaucoup",
        "mon", "ma", "me", "te", "se", "ne", "pas", "plus", "moins",
        "un", "une", "des", "le", "la", "les", "du", "de",
        "comme", "si", "ici", "par", "a", "l", "est",
        "avoir", "etre", "faire", "fait", "ete", "suis",
        "symptome", "symptomes", "signe", "douleur",
        "hier", "aujourdhui", "matin", "soir", "nuit",
    }
    qt_significatif = qt - STOPWORDS

    # ── 1. Maladies probables ──────────────────────────────────────────────
    maladies_probables = []
    for info in MALADIES:
        symptomes_mots = set()
        for s in info["symptomes"]:
            symptomes_mots.update(_tokens(s))
        score = _score_tokens(qt_significatif, symptomes_mots)
        if score >= 0.20:
            maladies_probables.append({
                "maladie": info["maladie"],
                "probabilite": round(info["probabilite"] * score, 2),
            })

    if not maladies_probables:
        maladies_probables.append({
            "maladie": "Symptomes non specifiques",
            "probabilite": 0.5,
        })

    noms_maladies = [m["maladie"] for m in maladies_probables]

    # ── 2. Recherche dans la base de symptomes ─────────────────────────────
    resultats_bruts = symptomes_db.rechercher_par_symptome(symptomes)

    # ── 3. Filtrage medicalement coherent ────────────────────────────────
    recommandations = []
    seen_noms = set()

    for r in resultats_bruts:
        nom = r["nom"].lower()
        classe = r["classe"]
        symptomes_list = r["symptomes"]

        if nom in seen_noms:
            continue
        seen_noms.add(nom)

        # Score medicament vs symptomes
        symptomes_tokens = set()
        for s in symptomes_list:
            symptomes_tokens.update(_tokens(s))
        score_medoc = _score_tokens(qt_significatif, symptomes_tokens)

        # Classe therapeutique coherente ?
        cls_ok = False
        for mal in noms_maladies:
            classes_ok = CLASSE_PAR_MALADIE.get(mal, [])
            for c in classes_ok:
                if _normaliser(c) in _normaliser(classe):
                    cls_ok = True
                    break
            if cls_ok:
                break

        if score_medoc >= 0.25 or cls_ok:
            recommandations.append({
                "nom": nom,
                "classe": classe,
                "symptomes": symptomes_list,
                "substances": r["substances"],
                "score": score_medoc,
            })

    recommandations.sort(key=lambda x: x["score"], reverse=True)

    # ── 4. Filtres : allergies ───────────────────────────────────────────
    substances_allergenes = set()
    if allergies:
        for a in allergies:
            a_norm = _normaliser(a)
            substances_allergenes.add(a_norm)
            for cle, info in symptomes_db.SYMPTOMES_MEDIAMENTS.items():
                for sub in info["substances"]:
                    sub_norm = _normaliser(sub)
                    if a_norm in sub_norm or sub_norm in a_norm:
                        substances_allergenes.add(sub_norm)

    recommandations_filtrees = []
    for rec in recommandations:
        if substances_allergenes:
            subst_set = {_normaliser(s) for s in rec["substances"]}
            if subst_set & substances_allergenes:
                continue
        recommandations_filtrees.append(rec)

    # ── 5. Format de sortie ─────────────────────────────────────────────
    recommandations_final = []
    for idx, rec in enumerate(recommandations_filtrees[:6]):
        recommandations_final.append({
            "medicament_id": 100 + idx,
            "nom": rec["nom"].capitalize(),
            "categorie": rec["classe"],
            "prix": _prix_par_classe(rec["classe"]),
            "disponible": True,
            "motif": "Indique pour : " + ", ".join(rec["symptomes"][:3]) + ".",
        })

    # ── 6. Alerte si aucun medicament trouve ────────────────────────────
    alerte = None
    if not recommandations_final:
        alerte = "Aucun medicament approprie pour vos symptomes. Consultez un professionnel de sante."

    if any(r["categorie"].lower() == "antibiotique" for r in recommandations_final):
        alerte = "Certains medicaments recommandes sont des antibiotiques. Consultez un medecin avant toute prise."

    return {
        "maladies_probables": sorted(maladies_probables, key=lambda x: x["probabilite"], reverse=True),
        "recommandations": recommandations_final,
        "alerte": alerte,
    }


def question_libre(question):
    if not RAG_DISPONIBLE:
        return {"reponse": "Service RAG momentanement indisponible."}
    try:
        docs = rag_rechercher(question, k=3, score_min=0.4)
        if docs:
            return {"reponse": docs[0]["texte"]}
        return {"reponse": "Je n'ai pas trouve de reponse precise a votre question."}
    except Exception:
        return {"reponse": "Erreur lors de la recherche. Reessayez."}
