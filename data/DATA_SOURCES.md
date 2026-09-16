# Sources de données médicaments

Ce dossier documente les sources de données utilisées pour enrichir la base de connaissances
du système de recommandation de médicaments de `Gestion Pharmacie IA`.

---

## 1. BDPM — Base de Données Publique des Médicaments (ANSM)

- **Statut** : ✅ déjà intégré dans `backend/app/ia/data/bdpm/`
- **URL** : https://base-donnees-publique.medicaments.gouv.fr/telechargement
- **Description** : Référentiel officiel français des spécialités, compositions, présentations et génériques.
- **Fichiers utilisés** :
  - `specialites.txt` — ~13 000 spécialités
  - `compositions.txt` — substances actives
  - `presentations.txt` — CIP, prix, remboursement
  - `generiques.txt` — groupes génériques
- **Mise à jour** : mensuelle par l'ANSM
- **Loader** : `backend/app/ia/bdpm_loader.py`

---

## 2. OpenMedic (ANSM) — Données de consommation / prescription

- **Statut** : 🔌 source externe à intégrer
- **URL** : https://www.ansm.sante.fr/dossiers-thematiques/open-data/open-medic
- **Description** : Données annuelles de consommation de médicaments en France (ville et hôpital).
- **Format** : CSV / Excel par année
- **Usage potentiel** : identifier les médicaments les plus prescrits, ajuster le stock, pondérer les recommandations.
- **Téléchargement** : manuel depuis l'URL (pas d'API publique stable).
- **Script d'ingestion** : `scripts/download_openmedic.py`

---

## 3. CIS_bdpm / CIS_CIP_bdpm — data.gouv.fr

- **Statut** : 🔌 source externe à intégrer
- **URL** : https://www.data.gouv.fr/fr/datasets/base-de-donnees-publique-des-medicaments/
- **Description** : Miroir data.gouv.fr de la BDPM, proposé en CSV (plus pratique que les .txt tabulés).
- **Fichiers** :
  - `CIS_bdpm.csv` — Code CIS ↔ dénomination, forme, voie, autorisation
  - `CIS_CIP_bdpm.csv` — Code CIS ↔ CIP7/CIP13 (présentations)
  - `CIS_COMPO_bdpm.csv` — substances actives
  - `CIS_HAS_SMR_bdpm.csv` — avis HAS
  - `CIS_HAS_ASMR_bdpm.csv` — amélioration du service médical rendu
- **Avantage** : format CSV stable, mise à jour quotidienne, lien direct.
- **Script d'ingestion** : `scripts/download_cis_bdpm.py`

---

## 4. RxNorm / OpenFDA (USA, anglais)

- **Statut** : 🔌 source externe à intégrer
- **URL** :
  - OpenFDA : https://open.fda.gov/data/downloads/
  - RxNorm (NLM) : https://www.nlm.nih.gov/research/umls/rxnorm/
- **Description** :
  - **OpenFDA** : labels, effets indésirables, rappels de médicaments commercialisés aux USA.
  - **RxNorm** : terminologie normalisée de médicaments (USAN, INN, marques), liens vers SNOMED CT.
- **Usage potentiel** : enrichir la synonymie symptôme ↔ substance active (INN ↔ DCI internationale).
- **Limite** : données en anglais, médicaments non commercialisés en France non pertinents.
- **API OpenFDA** : `https://api.fda.gov/drug/label.json?search=...`
- **Script d'ingestion** : `scripts/download_openfda.py`

---

## 5. WHO ATC Classification — classes thérapeutiques

- **Statut** : 🔌 source externe à intégrer
- **URL** : https://www.whocc.no/atc_ddd_index/
- **Description** : Classification ATC (Anatomical Therapeutic Chemical) de l'OMS, normalisée mondialement.
- **Format** : page HTML → à scraper (ou téléchargement annuel du fichier complet)
- **Niveaux** : 5 niveaux (groupe anatomique → substance chimique)
- **Usage potentiel** : classer automatiquement les médicaments par indication thérapeutique
  (ex. A03 = système digestif, A03F = antiémétiques → vomissement, nausées).
- **Script d'ingestion** : `scripts/download_who_atc.py`

---

## Schéma d'enrichissement

```
[BDPM txt] ─┐
[CIS CSV]  ─┤
[OpenMedic]─┼──> ingest/*.py ──> data/processed/medicaments_enrichis.json
[OpenFDA]  ─┤                            │
[WHO ATC]  ─┘                            ▼
                              symptomes_db.py (mapping auto)
                              knowledge_base.py
                              rag/index (FAISS)
```

L'enrichissement permet :
- d'ajouter les **vomissements** aux antiémétiques / antispasmodiques
- de couvrir les médicaments absents aujourd'hui (seulement ~58 actuellement)
- de pondérer les recommandations par la fréquence de prescription réelle

---

## Notes méthodologiques

- Les sources **US (RxNorm, OpenFDA)** sont secondaires : la base principale reste **BDPM/CIS** pour le marché français.
- Le mapping **symptôme ↔ classe ATC** n'est pas 1-pour-1 : il faut un mapping manuel ou une table de référence
  (ex. antiémétiques A03F → "nausées", "vomissement").
- Toute ingestion doit être versionnée et reproductible (script + checksum).
