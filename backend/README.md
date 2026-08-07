# Back-end — Binôme 3 (Eli, Hery, Luc)

API FastAPI : base de données des médicaments, gestion du stock (CRUD), vérification de la
quantité disponible, signalement des ruptures de stock.

- `app/` → code de l'API (`main.py`, routes, schémas)
- `db/` → base de données et migrations
- `tests/` → tests de l'API

Lancement :
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```
