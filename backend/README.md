# Back-end — Binôme 3 (Eli, Hery, Luc)

API FastAPI : base de données des médicaments, gestion du stock (CRUD), vérification de la
quantité disponible, signalement des ruptures de stock, et **recommandations IA** basées sur
le moteur `pharmacie-ai` (symptômes + RAG sentence-transformers / FAISS).

- `app/main.py` → API FastAPI (routes `/auth`, `/medicaments`, `/stock`, `/ia`)
- `app/ia_service.py` → service de recommandation IA (format du contrat `docs/api-contrat.md`)
- `app/ia/` → moteur IA réutilisé depuis `/home/harry/pharmacie-ai` (symptomes_db, BDPM, RAG)
- `app/ia/data/` → données BDPM + index FAISS + stock
- `db/` → fichiers de persistance JSON des médicaments/stock

## Installation

```bash
cd backend
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

> Les dépendances ML (torch CPU, transformers, sentence-transformers, faiss) sont lourdes.
> Le premier appel `/ia/recommandations` télécharge `all-MiniLM-L6-v2` (~90 Mo) puis le charge.

## Lancement

```bash
cd backend
venv/bin/uvicorn app.main:app --reload --port 8000
```

## Endpoints

| Méthode | Path | Description |
|---|---|---|
| POST | `/auth/login` | Login (`pharmacien1/secret`, `patient1/secret`, `admin/admin`) |
| GET | `/auth/me` | Utilisateur courant |
| GET/POST/PUT/DELETE | `/medicaments[/{id}]` | CRUD médicaments |
| GET | `/stock/ruptures` | Ruptures / alertes de stock |
| POST | `/stock/ajout` | Entrée de stock |
| POST | `/stock/vente` | Vente (décrémente le stock) |
| POST | `/ia/recommandations` | Recommandations IA à partir de symptômes |
| GET | `/ia/question` | Question libre via le RAG (bonus) |
| GET | `/health` | Health check |

## Exemple IA

```bash
curl -X POST http://localhost:8000/ia/recommandations \
  -H 'Content-Type: application/json' \
  -d '{"symptomes":"fièvre, maux de tête, courbatures","age":34,"allergies":["pénicilline"]}'
```