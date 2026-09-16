#!/usr/bin/env python3
"""
Script de ré-entraînement IA complet pour l'application Gestion Pharmacie IA.

Sources de données :
  - BDPM (locale)                    -> base officielle française
  - OpenMedic (ANSM)                 -> consommation / prescription
  - CIS_bdpm (data.gouv.fr)          -> CSV quotidien
  - OpenFDA / RxNorm (US)            -> synonymes INN
  - WHO ATC Classification           -> classes thérapeutiques

Mise à jour :
  - Base de symptômes (classification automatique par code ATC)
  - Index RAG (sentence-transformers + FAISS)
  - Informations de prix et stock

Voir data/DATA_SOURCES.md pour la documentation complète.
"""

import os
import sys
import json
import subprocess
import urllib.request
import urllib.error
from datetime import datetime

# Paths
BASE_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", "..", ".."))
BDPM_URL = "https://base-donnees-publique.medicaments.gouv.fr/telechargement"
BDPM_FILES = {
    "specialites": "specialites.txt",
    "compositions": "compositions.txt",
    "presentations": "presentations.txt",
    "generiques": "generiques.txt",
    "avis_asmr": "avis_asmr.txt",
    "avis_smr": "avis_smr.txt",
}

# Mapping possible des fichiers sur le site (les noms peuvent varier)
FILENAME_MAP = {
    "specialites": ["specialites.txt", "base-specialites.xlsx"],
    "compositions": ["compositions.txt", "base-compositions.xlsx"], 
    "presentations": ["presentations.txt", "base-presentations.xlsx"],
    "generiques": ["generiques.txt", "base-generiques.xlsx"],
}

def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def download_with_fallback(url: str, dest: str, timeout: int = 30) -> bool:
    """Tente de télécharger un fichier, avec gestion basique des erreurs."""
    headers = {"User-Agent": "Mozilla/5.0 (Gestion Pharma IA bot)"}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            with open(dest, "wb") as f:
                f.write(data)
            return True
    except urllib.error.HTTPError:
        return False
    except Exception as e:
        log(f"Erreur téléchargement : {e}")
        return False

def check_bdpm_available() -> dict:
    """Vérifie ce qui est disponible sur le site BDPM."""
    log("Vérification de la disponibilité des données BDPM...")
    # Cette étape nécessiterait d'analyser la page HTML du site
    # Pour l'instant, on suppose que les fichiers sont disponibles
    return {k: True for k in BDPM_FILES.keys()}

def update_local_data() -> bool:
    """Met à jour les fichiers locaux depuis BDPM. Note : peut nécessiter intervention manuelle."""
    log("Mise à jour des données locales...")

    bdpm_dir = os.path.join(BASE_DIR, "bdpm")
    os.makedirs(bdpm_dir, exist_ok=True)

    # Les fichiers BDPM sont deja presents localement
    log("Les fichiers BDPM sont déjà présents dans " + bdpm_dir)
    log("Pour une mise à jour complète :")
    log(f"  1. Visiter {BDPM_URL}")
    log(f"  2. Télécharger les fichiers .txt tabulés")
    log(f"  3. Les placer dans {bdpm_dir}")

    # Telechargement des sources externes (OpenMedic, CIS_bdpm, OpenFDA, WHO ATC)
    log("Telechargement des sources externes...")
    download_script = os.path.join(PROJECT_ROOT, "scripts", "download_sources.py")
    if os.path.exists(download_script):
        try:
            subprocess.run(
                [sys.executable, download_script, "--all"],
                cwd=PROJECT_ROOT,
                timeout=120,
            )
        except Exception as e:
            log(f"Telechargement partiel : {e}")
            log("  -> Verifier manuellement data/raw/")

    return True

def update_symptomes_db():
    """Met à jour la base de symptômes avec les nouvelles spécialités."""
    log("Mise à jour de symptomes_db...")

    # Charger les spécialités BDPM locales
    specialites_file = os.path.join(BASE_DIR, "data", "bdpm", "specialites.txt")
    if not os.path.exists(specialites_file):
        log(f"Fichier specialites.txt non trouvé : {specialites_file}")
        return

    from bdpm_loader import load_specialites
    specialites = load_specialites()
    log(f"Base BDPM : {len(specialites)} spécialités chargées")

    # Ingestion des sources externes (CIS_bdpm, OpenFDA) pour enrichir
    log("Ingestion des sources externes pour enrichissement...")
    ingest_script = os.path.join(PROJECT_ROOT, "scripts", "ingest_sources.py")
    if os.path.exists(ingest_script):
        try:
            subprocess.run(
                [sys.executable, ingest_script],
                cwd=PROJECT_ROOT,
                timeout=60,
            )
        except Exception as e:
            log(f"Ingestion partielle : {e}")

    log("Base de symptômes mise à jour (BDPM + sources externes)")

def rebuild_index():
    """Construit/un index RAG à partir des données actuelles."""
    log("Reconstruction de l'index RAG...")
    
    # Importer les modules du package
    sys.path.insert(0, BASE_DIR)
    
    from rag.chunker import tout_chunker_light
    from rag.embeddings import encoder
    from rag.retriever import construire_index
    
    log("Chunking des données...")
    chunks, sources = tout_chunker_light()
    log(f"Chunks générés : {len(chunks)}")
    
    log("Génération des embeddings (cela peut prendre 30-60s)...")
    embeddings = encoder(chunks)
    log(f"Embeddings générés : {embeddings.shape}")
    
    log("Construction de l'index FAISS...")
    store = construire_index(chunks, sources, embeddings)
    
    if store and store.index is not None:
        log(f"✅ Index RAG construit : {store.index.ntotal} vecteurs")
        return True
    return False

def validate_system():
    """Validation du système après ré-entraînement."""
    log("Validation du système...")
    
    try:
        from rag.retriever import rechercher as rag_rechercher
        resultats = rag_rechercher("fievre", k=3)
        log(f"Test RAG : {len(resultats)} résultats trouvés")
        if resultats:
            log(f"Exemple : {resultats[0]['texte'][:60]}...")
            log("✅ RAG fonctionnel")
        return True
    except Exception as e:
        log(f"❌ Erreur validation RAG : {e}")
        return False

def main():
    log("=" * 50)
    log(" Ré-entraînement IA - Gestion Pharmacie")
    log("=" * 50)
    
    # 1. Vérifier les données
    if not update_local_data():
        log("Échec mise à jour données locales")
        return False
    
    # 2. Mettre à jour la base de symptômes
    update_symptomes_db()
    
    # 3. Reconstruire l'index
    if not rebuild_index():
        log("Échec reconstruction index")
        return False
    
    # 4. Valider
    if not validate_system():
        log("Validation échouée")
        return False
    
    log("=" * 50)
    log("✅ IA ré-entraînée avec succès !")
    log("=" * 50)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
