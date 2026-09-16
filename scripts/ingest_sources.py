#!/usr/bin/env python3
"""
Ingestion des sources de données externes vers la base interne.

Transforme les fichiers bruts (data/raw/) en JSON normalisé
(data/processed/medicaments_enrichis.json) puis enrichit symptomes_db.py.

Mapping symptomatique :
  - Anti-emetiques (ATC A03F, A04A) -> vomissement, nausees
  - Antispasmodiques (ATC A03A)    -> spasmes, douleurs abdominales
  - Antidiarrheiques (ATC A07)     -> diarrhee
  - IPP (ATC A02BC)                -> reflux, brulures d'estomac
  - Antalgiques (ATC N02)          -> douleur, fievre
  - AINS (ATC M01A)                -> inflammation, douleur
  - Antibiotiques (ATC J01)        -> infection, angine

Usage :
    python scripts/ingest_sources.py
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
PROCESSED.mkdir(parents=True, exist_ok=True)

# Mapping ATC -> classe therapeutique + symptomes
ATC_MAPPING = {
    "A02BC": {"classe": "IPP",          "symptomes": ["reflux", "brûlures d'estomac", "ulcère"]},
    "A03A":  {"classe": "Antispasmodique", "symptomes": ["spasmes", "douleurs abdominales", "ventre"]},
    "A03F":  {"classe": "Antiémétique", "symptomes": ["vomissement", "nausées"]},
    "A04A":  {"classe": "Antiémétique", "symptomes": ["vomissement", "nausées"]},
    "A07":   {"classe": "Antidiarrhéique", "symptomes": ["diarrhée"]},
    "A07B":  {"classe": "Adsorbant intestinal", "symptomes": ["diarrhée", "ballonnements"]},
    "A07D":  {"classe": "Antipéristaltique", "symptomes": ["diarrhée"]},
    "J01":   {"classe": "Antibiotique", "symptomes": ["infection"]},
    "J01C":  {"classe": "Antibiotique (Pénicilline)", "symptomes": ["infection", "angine", "otite"]},
    "M01A":  {"classe": "AINS",          "symptomes": ["douleur", "inflammation", "fièvre"]},
    "N02":   {"classe": "Antalgique",    "symptomes": ["douleur"]},
    "N02BE": {"classe": "Antalgique / Antipyrétique", "symptomes": ["douleur", "fièvre"]},
    "N05B":  {"classe": "Anxiolytique",  "symptomes": ["anxiété", "insomnie"]},
    "R03":   {"classe": "Bronchodilatateur", "symptomes": ["asthme", "essoufflement"]},
    "R05":   {"classe": "Antitussif",    "symptomes": ["toux"]},
    "R06":   {"classe": "Antihistaminique", "symptomes": ["allergie", "urticaire"]},
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def atc_to_symptoms(atc_code: str) -> dict:
    """Retourne la classe et les symptomes associes a un code ATC."""
    if not atc_code:
        return None
    code = atc_code.upper().strip()
    for prefix, info in ATC_MAPPING.items():
        if code.startswith(prefix):
            return info
    return None


def ingest_cis_bdpm():
    """Parse le CSV CIS_bdpm et produit la liste enrichie."""
    src = RAW / "cis_bdpm.csv"
    if not src.exists():
        log(f"Fichier absent : {src}")
        log("  -> Executer scripts/download_sources.py --source cis")
        log("  -> Ou telecharger manuellement depuis data.gouv.fr")
        return []

    log(f"Lecture {src.name}...")
    medicaments = []
    with open(src, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            nom = (row.get("denomination") or "").strip().lower()
            atc = (row.get("code_atc") or "").strip()
            if not nom:
                continue
            mapping = atc_to_symptoms(atc)
            if not mapping:
                continue
            medicaments.append({
                "nom": nom,
                "cis": row.get("cis"),
                "forme": row.get("forme_pharmaceutique"),
                "voie": row.get("voie_administration"),
                "atc": atc,
                **mapping,
                "source": "CIS_bdpm",
            })
    log(f"  -> {len(medicaments)} medicaments avec mapping ATC")
    return medicaments


def ingest_openfda():
    """Enrichit avec les anti-emetiques US (OpenFDA) pour synonymes INN."""
    src = RAW / "openfda_label_sample.json"
    if not src.exists():
        log(f"OpenFDA absent : {src} (ignore)")
        return []
    try:
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log(f"  Erreur lecture OpenFDA : {e}")
        return []

    extras = []
    for result in data.get("results", []):
        openfda = result.get("openfda", {})
        generic_names = openfda.get("generic_name", [])
        indications = result.get("indications_and_usage", [])
        is_antiemetic = any("nausea" in i.lower() or "vomit" in i.lower()
                            for i in indications if isinstance(i, str))
        if is_antiemetic and generic_names:
            extras.append({
                "nom": generic_names[0].lower(),
                "substances": [g.upper() for g in generic_names[:3]],
                "symptomes": ["vomissement", "nausées"],
                "classe": "Antiémétique (US)",
                "source": "OpenFDA",
            })
    log(f"  -> {len(extras)} medicaments US avec indication nausees/vomissement")
    return extras


def merge_with_existing(nouveaux):
    """Fusionne avec symptomes_db.py pour ne pas ecraser le curation manuelle."""
    sys.path.insert(0, str(ROOT / "backend" / "app" / "ia"))
    from symptomes_db import SYMPTOMES_MEDIAMENTS

    existants = {n.lower() for n in SYMPTOMES_MEDIAMENTS.keys()}
    ajoutes = 0
    for m in nouveaux:
        nom = m["nom"]
        if nom in existants:
            continue
        SYMPTOMES_MEDIAMENTS[nom] = {
            "substances": m.get("substances", []),
            "symptomes": m["symptomes"],
            "classe": m["classe"],
        }
        ajoutes += 1
        existants.add(nom)
    log(f"  -> {ajoutes} nouveaux medicaments ajoutes (non ecrases)")
    return SYMPTOMES_MEDIAMENTS, ajoutes


def write_enriched(db, ajoutes):
    """Reecrit symptomes_db.py avec les ajouts."""
    path = ROOT / "backend" / "app" / "ia" / "symptomes_db.py"
    content = "SYMPTOMES_MEDIAMENTS = {\n"
    for nom, info in sorted(db.items()):
        content += f'    "{nom}": {{\n'
        content += f'        "substances": {info["substances"]!r},\n'
        content += f'        "symptomes": {info["symptomes"]!r},\n'
        content += f'        "classe": {info["classe"]!r}\n'
        content += f'    }},\n'
    content += "}\n\n"
    content += '''def normaliser(texte):
    """Supprime les accents et met en minuscule pour un matching robuste."""
    replacements = {
        "à": "a", "â": "a", "ä": "a",
        "é": "e", "è": "e", "ê": "e", "ë": "e",
        "î": "i", "ï": "i",
        "ô": "o", "ö": "o",
        "ù": "u", "û": "u", "ü": "u",
        "ç": "c", "œ": "oe", "æ": "ae",
    }
    texte = texte.lower().strip()
    for src, dst in replacements.items():
        texte = texte.replace(src, dst)
    return texte


def rechercher_par_symptome(symptome):
    symptome_norm = normaliser(symptome)
    resultats = []

    for nom, info in SYMPTOMES_MEDIAMENTS.items():
        score = 0
        for s in info["symptomes"]:
            s_norm = normaliser(s)
            if symptome_norm in s_norm or s_norm in symptome_norm:
                score += 2
            elif symptome_norm.split()[0] in s_norm:
                score += 1

        if score > 0:
            resultats.append({
                "nom": nom,
                "classe": info["classe"],
                "symptomes": info["symptomes"],
                "substances": info["substances"],
                "score": score
            })

    resultats.sort(key=lambda x: x["score"], reverse=True)
    return resultats

def get_symptomes_medoc(nom):
    nom_lower = nom.lower()
    for cle, info in SYMPTOMES_MEDIAMENTS.items():
        if nom_lower in cle or cle in nom_lower:
            return info
    return None

def lister_classes():
    classes = set()
    for info in SYMPTOMES_MEDIAMENTS.values():
        classes.add(info["classe"])
    return sorted(classes)

def lister_symptomes():
    symptomes = set()
    for info in SYMPTOMES_MEDIAMENTS.values():
        symptomes.update(info["symptomes"])
    return sorted(symptomes)
'''
    path.write_text(content, encoding="utf-8")
    log(f"  -> {path} ecrit ({ajoutes} ajouts)")


def main():
    log("=== Ingestion des sources externes ===")
    tous = []
    tous.extend(ingest_cis_bdpm())
    tous.extend(ingest_openfda())

    out = PROCESSED / "medicaments_enrichis.json"
    out.write_text(json.dumps(tous, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"  -> {len(tous)} medicaments ecrits dans {out.name}")

    if tous:
        db, ajoutes = merge_with_existing(tous)
        if ajoutes > 0:
            write_enriched(db, ajoutes)
            log(f"  -> {ajoutes} medicaments ajoutes a symptomes_db.py")
        else:
            log("  -> Aucun nouveau medicament a ajouter")

    log("=== Termine ===")
    log("Note : le reentrainement effectif necessite les donnees brutes dans data/raw/")
    log("       Telechargement : python scripts/download_sources.py --all")


if __name__ == "__main__":
    main()
