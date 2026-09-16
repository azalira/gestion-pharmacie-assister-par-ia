"""API FastAPI — Gestion Pharmacie IA.

Implémente le contrat d'API (docs/api-contrat.md) pour le binôme 4 (frontend).
Le service IA (/ia/recommandations) s'appuie sur le moteur de pharmacie-ai
(symptomes_db + RAG sentence-transformers + FAISS).
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.ia_service import recommander

# ---------------------------------------------------------------------------
# Gestion du stock / médicaments (démo : en mémoire, persistance JSON)
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(__file__), "db")
MEDICAMENTS_FILE = os.path.join(DATA_DIR, "medicaments.json")
STOCK_FILE = os.path.join(DATA_DIR, "stock.json")


def _charger(fichier, defaut):
    if os.path.exists(fichier):
        try:
            import json
            with open(fichier, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return defaut
    return defaut


def _sauver(fichier, data):
    import json
    os.makedirs(os.path.dirname(fichier), exist_ok=True)
    with open(fichier, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# --- Comptes ---

USERS = {
    "pharmacien1": {
        "id": 1,
        "username": "pharmacien1",
        "password": "secret",
        "full_name": "Eli Raz",
        "role": "pharmacien",
    },
    "patient1": {
        "id": 2,
        "username": "patient1",
        "password": "secret",
        "full_name": "Patient Démo",
        "role": "patient",
    },
    "admin": {
        "id": 3,
        "username": "admin",
        "password": "admin",
        "full_name": "Administrateur",
        "role": "admin",
    },
}


def _user_public(u):
    return {k: v for k, v in u.items() if k != "password"}


# --- Médicaments ---

def _medicaments_par_defaut():
    return [
        {"id": 1, "nom": "Paracétamol 500mg", "categorie": "Antalgique", "prix": 1500,
         "quantite_stock": 120, "seuil_alerte": 20, "date_expiration": "2027-06-30", "fournisseur_id": 3},
        {"id": 2, "nom": "Ibuprofène 400mg", "categorie": "Antalgique", "prix": 2000,
         "quantite_stock": 80, "seuil_alerte": 15, "date_expiration": "2027-12-31", "fournisseur_id": 2},
        {"id": 3, "nom": "Amoxicilline 500mg", "categorie": "Antibiotique", "prix": 3500,
         "quantite_stock": 45, "seuil_alerte": 10, "date_expiration": "2026-11-15", "fournisseur_id": 1},
        {"id": 4, "nom": "Vitamine C 1000mg", "categorie": "Complément", "prix": 2500,
         "quantite_stock": 0, "seuil_alerte": 10, "date_expiration": "2028-03-01", "fournisseur_id": 2},
        {"id": 5, "nom": "Aspirine 500mg", "categorie": "Antalgique", "prix": 1200,
         "quantite_stock": 5, "seuil_alerte": 20, "date_expiration": "2027-01-20", "fournisseur_id": 3},
    ]


def _charger_medicaments():
    return _charger(MEDICAMENTS_FILE, _medicaments_par_defaut())


def _sauver_medicaments(meds):
    _sauver(MEDICAMENTS_FILE, meds)


_medicaments = _charger_medicaments()
_next_id = max((m["id"] for m in _medicaments), default=0) + 1


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Gestion Pharmacie IA", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _current_user(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(401, "Non authentifié")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(401, "Token invalide")
    # Token demo : on retrouve l'utilisateur via le token (id-encodé de façon simple)
    for u in USERS.values():
        expected = f"token-{u['id']}-demo"
        if token == expected:
            return _user_public(u)
    raise HTTPException(401, "Token invalide")


def _require(role: str, user=None):
    if user is None:
        raise HTTPException(401, "Non authentifié")
    if role not in ("pharmacien", "admin") or user["role"] not in ("pharmacien", "admin"):
        raise HTTPException(403, "Rôle insuffisant")


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class MedicamentIn(BaseModel):
    nom: str
    categorie: str
    prix: float = Field(ge=0)
    quantite_stock: int = Field(ge=0)
    seuil_alerte: int = Field(ge=0)
    date_expiration: Optional[str] = None
    fournisseur_id: Optional[int] = None


class MedicamentPatch(BaseModel):
    nom: Optional[str] = None
    categorie: Optional[str] = None
    prix: Optional[float] = Field(default=None, ge=0)
    quantite_stock: Optional[int] = Field(default=None, ge=0)
    seuil_alerte: Optional[int] = Field(default=None, ge=0)
    date_expiration: Optional[str] = None
    fournisseur_id: Optional[int] = None


class StockAjout(BaseModel):
    medicament_id: int
    quantite: int = Field(ge=1)


class StockVente(BaseModel):
    medicament_id: int
    quantite: int = Field(ge=1)
    client: Optional[str] = ""


class RecommandationRequest(BaseModel):
    symptomes: str
    age: Optional[int] = None
    allergies: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@app.post("/auth/login")
def login(body: LoginRequest, authorization: Optional[str] = Header(None)):
    u = USERS.get(body.username)
    if not u or u["password"] != body.password:
        raise HTTPException(401, "Identifiants invalides")
    return {
        "access_token": f"token-{u['id']}-demo",
        "token_type": "bearer",
        "user": _user_public(u),
    }


@app.get("/auth/me")
def me(authorization: Optional[str] = Header(None)):
    return _current_user(authorization)


# ---------------------------------------------------------------------------
# Médicaments
# ---------------------------------------------------------------------------

@app.get("/medicaments")
def lister_medicaments(
    search: str = "",
    categorie: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    authorization: Optional[str] = Header(None),
):
    _require("pharmacien", _current_user(authorization))
    items = _medicaments
    if search:
        s = search.lower()
        items = [m for m in items if s in m["nom"].lower() or s in m["categorie"].lower()]
    if categorie:
        items = [m for m in items if m["categorie"].lower() == categorie.lower()]
    total = len(items)
    start = (page - 1) * limit
    return {"items": items[start:start + limit], "total": total, "page": page}


@app.get("/medicaments/{med_id}")
def detail_medicament(med_id: int, authorization: Optional[str] = Header(None)):
    _require("pharmacien", _current_user(authorization))
    for m in _medicaments:
        if m["id"] == med_id:
            return m
    raise HTTPException(404, "Médicament introuvable")


@app.post("/medicaments", status_code=200)
def creer_medicament(body: MedicamentIn, authorization: Optional[str] = Header(None)):
    _require("pharmacien", _current_user(authorization))
    global _next_id
    if any(m["nom"].lower() == body.nom.lower() for m in _medicaments):
        raise HTTPException(409, "Doublon : ce médicament existe déjà")
    med = body.model_dump()
    med["id"] = _next_id
    _next_id += 1
    _medicaments.append(med)
    _sauver_medicaments(_medicaments)
    return med


@app.put("/medicaments/{med_id}")
def maj_medicament(med_id: int, body: MedicamentPatch, authorization: Optional[str] = Header(None)):
    _require("pharmacien", _current_user(authorization))
    for i, m in enumerate(_medicaments):
        if m["id"] == med_id:
            for k, v in body.model_dump(exclude_unset=True).items():
                if v is not None:
                    m[k] = v
            _sauver_medicaments(_medicaments)
            return m
    raise HTTPException(404, "Médicament introuvable")


@app.delete("/medicaments/{med_id}", status_code=204)
def supprimer_medicament(med_id: int, authorization: Optional[str] = Header(None)):
    _require("pharmacien", _current_user(authorization))
    global _medicaments
    for i, m in enumerate(_medicaments):
        if m["id"] == med_id:
            del _medicaments[i]
            _sauver_medicaments(_medicaments)
            return None
    raise HTTPException(404, "Médicament introuvable")


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

@app.get("/stock/ruptures")
def ruptures(authorization: Optional[str] = Header(None)):
    _require("pharmacien", _current_user(authorization))
    items = []
    for m in _medicaments:
        if m["quantite_stock"] <= m["seuil_alerte"]:
            items.append({
                "id": m["id"],
                "nom": m["nom"],
                "quantite_stock": m["quantite_stock"],
                "seuil_alerte": m["seuil_alerte"],
                "etat": "rupture" if m["quantite_stock"] == 0 else "alerte",
            })
    return {"items": items}


@app.post("/stock/ajout")
def ajout_stock(body: StockAjout, authorization: Optional[str] = Header(None)):
    _require("pharmacien", _current_user(authorization))
    for m in _medicaments:
        if m["id"] == body.medicament_id:
            m["quantite_stock"] += body.quantite
            _sauver_medicaments(_medicaments)
            return {
                "id": m["id"],
                "quantite_stock": m["quantite_stock"],
                "message": "Stock mis à jour",
            }
    raise HTTPException(404, "Médicament introuvable")


@app.post("/stock/vente")
def vente_stock(body: StockVente, authorization: Optional[str] = Header(None)):
    _require("pharmacien", _current_user(authorization))
    for m in _medicaments:
        if m["id"] == body.medicament_id:
            if body.quantite > m["quantite_stock"]:
                raise HTTPException(409, "Stock insuffisant")
            m["quantite_stock"] -= body.quantite
            _sauver_medicaments(_medicaments)
            return {
                "id": m["id"],
                "quantite_stock": m["quantite_stock"],
                "vente_id": int(time.time()) % 100000,
            }
    raise HTTPException(404, "Médicament introuvable")


# ---------------------------------------------------------------------------
# IA — Recommandations
# ---------------------------------------------------------------------------

@app.post("/ia/recommandations")
def recommandations(body: RecommandationRequest):
    """L'IA étudie les symptômes et retourne des médicaments recommandés (RAG + base symptômes)."""
    if not body.symptomes or not body.symptomes.strip():
        raise HTTPException(422, "Le champ symptomes ne peut pas être vide")
    try:
        return recommander(body.symptomes, age=body.age, allergies=body.allergies)
    except ValueError as e:
        raise HTTPException(422, str(e))
    except Exception as e:
        print("ERREUR IA:", repr(e))
        raise HTTPException(503, "Modèle IA non chargé")


@app.get("/ia/question")
def ia_question(q: str = Query("", max_length=500)):
    """Question libre via le RAG (bonus)."""
    from app.ia_service import question_libre
    return question_libre(q)


@app.get("/health")
def health():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}