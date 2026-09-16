# Gestion Pharmacie IA

Application de recommandation de médicaments : l'IA étudie les symptômes du patient et recommande des médicaments selon le stock disponible.

> Dépôt GitHub : <https://github.com/azalira/gestion-pharmacie-assister-par-ia>

## Structure du projet

```
├── data/          # Binôme 1 — Préparation des données (collecte, nettoyage, EDA, train/test, scaling)
├── ml/            # Binôme 2 — Analyse et IA (création, entraînement, évaluation, optimisation du modèle)
├── backend/       # Binôme 3 — Back-end (API, base de données, gestion du stock, ruptures)
├── frontend/      # Binôme 4 — Interface admin et user (pharmacien, admin, patient)
└── docs/          # Documentation, comptes-rendus
```

## Binômes

| Binôme | Membres | Rôle | Dossier |
|--------|---------|------|---------|
| 1 | Larissa, Fideline | Préparation des données | `data/` |
| 2 | Harilaza | Analyse et IA | `ml/` |
| 3 | Eli, Hery Luc | Back-end et gestion des médicaments | `backend/` |
| 4 | Laryah, Joseph | Interface admin et user | `frontend/` |

## Branches

- `main` → code stable validé
- `develop` → intégration des travaux des binômes
- `feature/data-prep`, `feature/ia-model`, `feature/backend`, `feature/frontend` → travail des binômes

## Stack

- **Back-end** : FastAPI + SQLite
- **Frontend** : SvelteKit (Svelte 5 + TypeScript), compilé en statique servi par FastAPI
- **IA** : Python (scikit-learn / etc.)

## Lancement de l'application

### 1. Back-end + IA (port 8000)

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt   # la première fois
./venv/bin/uvicorn app.main:app --reload --port 8000
```

Le premier appel `/ia/recommandations` télécharge le modèle `all-MiniLM-L6-v2` (~90 Mo).

### 2. Frontend (port 5173)

```bash
cd frontend
npm install
npm run dev
```

## Entraîner l'IA sur les GPU gratuits de Kaggle

Le fine-tuning du chatbot (TinyLlama + QLoRA) tourne sur les **GPU T4 gratuits de Kaggle**,
sans GPU local. Tout est automatisé par un seul script :

```bash
# 0. Une seule fois : authentification Kaggle
kaggle auth login                       # OAuth (ou ~/.kaggle/kaggle.json / KAGGLE_API_TOKEN)

# 1. Vérifier l'environnement (données, notebook, bibliothèque kaggle)
python3 scripts/kaggle_gpu.py check

# 2. Préparer les données + métadonnées, puis pousser sur Kaggle
python3 scripts/kaggle_gpu.py all --wait    # --wait : reste accroché jusqu'à la fin

# 3. Récupérer le modèle LoRA entraîné → ml/models/pharma_bot_v1/
python3 scripts/kaggle_gpu.py output
```

Détail des étapes : `check` (diagnostic), `prepare` (données + métadonnées locales),
`push` (upload dataset + notebook, **l'entraînement démarre automatiquement sur GPU**),
`status [--wait]` (suivi de session), `output` (téléchargement + décompression du modèle).

Fichiers concernés :

| Fichier | Rôle |
|---|---|
| `kaggle_submission/kaggle_config.json` | Config (username Kaggle, slugs, GPU T4) |
| `ml/notebooks/kaggle_train.ipynb` | Notebook exécuté sur Kaggle (QLoRA TinyLlama) |
| `scripts/generate_kaggle_notebook.py` | Régénère le notebook : `python3 scripts/generate_kaggle_notebook.py` |
| `scripts/kaggle_gpu.py` | Pipeline complet (check / prepare / push / status / output) |

Quota Kaggle : ~30 h de GPU par semaine, gratuites. Le modèle entraîné est récupéré via
`scripts/kaggle_gpu.py output` puis servi par `ml/src/predict.py`.

## Rôles gérés
- **Pharmacien / Admin** : dashboard, CRUD médicaments, gestion du stock (ajout, vente, alertes de rupture)
- **Patient** : saisie des symptômes → recommandations IA selon le stock disponible

## Comptes de démonstration
- `pharmacien1` / `secret`
- `patient1` / `secret`
- `admin` / `admin`
