import os

BDPM_DIR = os.path.join(os.path.dirname(__file__), "data", "bdpm")

def load_specialites():
    fichier = os.path.join(BDPM_DIR, "specialites.txt")
    if not os.path.exists(fichier):
        return []
    
    with open(fichier, "r", encoding="latin-1") as f:
        lignes = f.readlines()
    
    resultats = []
    for ligne in lignes:
        parties = ligne.strip().split("\t")
        if len(parties) >= 10:
            resultats.append({
                "cis": parties[0],
                "nom": parties[1],
                "forme": parties[2],
                "voie": parties[3],
                "statut": parties[4],
                "procedure": parties[5],
                "commercialise": parties[6],
                "date_autorisation": parties[7],
                "titulaire": parties[9] if len(parties) > 9 else "",
                "is generique": parties[10] if len(parties) > 10 else ""
            })
    return resultats

def rechercher_medoc(query):
    specialites = load_specialites()
    query_lower = query.lower()
    
    resultats = []
    for s in specialites:
        if query_lower in s["nom"].lower():
            resultats.append(s)
    
    return resultats[:20]

def get_info_cis(cis):
    specialites = load_specialites()
    for s in specialites:
        if s["cis"] == cis:
            return s
    return None

def load_compositions():
    fichier = os.path.join(BDPM_DIR, "compositions.txt")
    if not os.path.exists(fichier):
        return {}
    
    with open(fichier, "r", encoding="latin-1") as f:
        lignes = f.readlines()
    
    compositions = {}
    for ligne in lignes:
        parties = ligne.strip().split("\t")
        if len(parties) >= 5:
            cis = parties[0]
            if cis not in compositions:
                compositions[cis] = []
            compositions[cis].append({
                "substance": parties[4],
                "dosage": parties[3] if len(parties) > 3 else "",
                "designation": parties[2] if len(parties) > 2 else ""
            })
    return compositions

def load_prix():
    fichier = os.path.join(BDPM_DIR, "presentations.txt")
    if not os.path.exists(fichier):
        return {}
    
    with open(fichier, "r", encoding="latin-1") as f:
        lignes = f.readlines()
    
    prix = {}
    for ligne in lignes:
        parties = ligne.strip().split("\t")
        if len(parties) >= 11:
            cis = parties[0]
            if cis not in prix:
                prix[cis] = []
            try:
                prix_public = float(parties[9].replace(",", ".")) if parties[9] else 0
            except:
                prix_public = 0
            prix[cis].append({
                "cip7": parties[1],
                "libelle": parties[2],
                "prix": prix_public,
                "remboursement": parties[10] if len(parties) > 10 else ""
            })
    return prix

def count_medicaments():
    specialites = load_specialites()
    return len(specialites)
