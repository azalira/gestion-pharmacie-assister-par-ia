#!/usr/bin/env python3
"""
Téléchargement des sources de données médicaments externes.

Sources :
  1. BDPM (txt tabulés)         -> deja dans backend/app/ia/data/bdpm/
  2. OpenMedic (ANSM)           -> CSV annuel, telechargement manuel recommande
  3. CIS_bdpm (data.gouv.fr)    -> CSV quotidien, telechargement direct
  4. OpenFDA / RxNorm           -> API REST
  5. WHO ATC Classification     -> scraping HTML

Usage :
    python scripts/download_sources.py --source openmedic
    python scripts/download_sources.py --source cis
    python scripts/download_sources.py --source openfda
    python scripts/download_sources.py --source atc
    python scripts/download_sources.py --all

Note : ce script necessite un acces Internet. Si le telechargement echoue,
les donnees brutes peuvent etre placees manuellement dans data/raw/.
"""

import argparse
import hashlib
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Gestion-Pharma-IA/1.0)"}

# URLs des sources
URLS = {
    # data.gouv.fr - Base de donnees publique des medicaments (CSV quotidien)
    "cis_bdpm":       "https://www.data.gouv.fr/fr/datasets/r/5c6da37c-6f04-4d70-be2a-7867f9b9b6f4",
    "cis_cip_bdpm":   "https://www.data.gouv.fr/fr/datasets/r/fb8d0c2c-3c5b-4b8a-9d3b-3b9c5a4a0a0a",
    "cis_compo_bdpm": "https://www.data.gouv.fr/fr/datasets/r/4d8a3e3c-3a3a-4d3a-8a3a-3a3a3a3a3a3a",
    # OpenFDA - API publique
    "openfda_label":  "https://api.fda.gov/drug/label.json?limit=100",
    # RxNorm - API REST
    "rxnorm":         "https://rxnav.nlm.nih.gov/REST/rxcui.json?name=paracetamol",
    # WHO ATC - page HTML (a scraper)
    "who_atc":        "https://www.whocc.no/atc_ddd_index/",
}


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, timeout: int = 60) -> bool:
    log(f"Telechargement {url} -> {dest.name}")
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
        dest.write_bytes(data)
        log(f"  OK ({len(data)} octets, sha256={sha256(dest)[:12]}...)")
        return True
    except urllib.error.HTTPError as e:
        log(f"  HTTP {e.code} - URL probablement changee, telechargement manuel necessaire")
    except urllib.error.URLError as e:
        log(f"  Erreur reseau : {e.reason}")
    except TimeoutError:
        log(f"  Timeout apres {timeout}s")
    return False


def download_cis_bdpm():
    log("=== CIS_bdpm (data.gouv.fr) ===")
    out = RAW / "cis_bdpm.csv"
    ok = download(URLS["cis_bdpm"], out)
    if not ok:
        log("  -> Telechargement manuel : https://www.data.gouv.fr/fr/datasets/base-de-donnees-publique-des-medicaments/")
    return ok


def download_openfda_label():
    log("=== OpenFDA (api.fda.gov) ===")
    out = RAW / "openfda_label_sample.json"
    url = "https://api.fda.gov/drug/label.json?search=indications_and_usage:nausea&limit=50"
    return download(url, out)


def download_rxnorm():
    log("=== RxNorm (NLM) ===")
    out = RAW / "rxnorm_sample.json"
    return download(URLS["rxnorm"], out)


def download_openmedic():
    log("=== OpenMedic (ANSM) ===")
    log("  Pas d'URL stable pour telechargement automatique.")
    log("  -> Telechargement manuel : https://www.ansm.sante.fr/dossiers-thematiques/open-data/open-medic")
    log("  -> Deplacer le ZIP extrait dans data/raw/openmedic/")
    target = RAW / "openmedic" / "README.txt"
    target.parent.mkdir(exist_ok=True)
    target.write_text(
        "Deposer ici les CSV OpenMedic telecharges depuis l'ANSM.\n"
        "URL : https://www.ansm.sante.fr/dossiers-thematiques/open-data/open-medic\n"
        f"Date de telechargement : {datetime.now().isoformat()}\n",
        encoding="utf-8",
    )
    return False


def download_atc():
    log("=== WHO ATC Classification ===")
    log("  Pas d'API publique, necessite scraping HTML.")
    log("  -> URL : https://www.whocc.no/atc_ddd_index/")
    log("  -> Ou telecharger le fichier annuel : https://www.whocc.no/atc_ddd_index/")
    target = RAW / "who_atc" / "README.txt"
    target.parent.mkdir(exist_ok=True)
    target.write_text(
        "Deposer ici le fichier WHO ATC (HTML scrape ou export).\n"
        "URL : https://www.whocc.no/atc_ddd_index/\n"
        f"Date de telechargement : {datetime.now().isoformat()}\n",
        encoding="utf-8",
    )
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=list(URLS.keys()) + ["openmedic", "atc", "all"])
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    targets = []
    if args.all or args.source in (None,):
        parser.error("Specifier --source ou --all")
    if args.all:
        targets = ["cis_bdpm", "openfda_label", "rxnorm", "openmedic", "atc"]
    else:
        targets = [args.source]

    results = {}
    for t in targets:
        fn = globals().get(f"download_{t}")
        if fn is None:
            log(f"Source inconnue : {t}")
            continue
        results[t] = fn()

    log("=" * 50)
    log("Resume :")
    for k, v in results.items():
        log(f"  {k}: {'OK' if v else 'manuel'}")
    log("=" * 50)
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
