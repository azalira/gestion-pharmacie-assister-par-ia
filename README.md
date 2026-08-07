# Gestion Pharmacie IA

Application de recommandation de médicaments : l'IA étudie les symptômes du patient et recommande des médicaments selon le stock disponible.

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
| 3 | Eli, Hery, Luc | Back-end et gestion des médicaments | `backend/` |
| 4 | Laryah, Joseph | Interface admin et user | `frontend/` |

## Branches

- `main` → code stable validé
- `develop` → intégration des travaux des binômes
- `feature/data-prep`, `feature/ia-model`, `feature/backend`, `feature/frontend` → travail des binômes

## Stack

- **Back-end** : FastAPI + SQLite
- **Frontend** : HTML/JS statique servi par FastAPI
- **IA** : Python (scikit-learn / etc.)
