# Contrat d'API — Gestion Pharmacie IA

Ce document est la **référence unique** entre le **frontend SvelteKit** (binôme 4)
et le **backend FastAPI** (binôme 3). Toute modification d'un endpoint doit être
répercutée ici avant merge.

Base URL (dev) : `http://localhost:8000`
Authentification : `Authorization: Bearer <token>` (sauf endpoints publics `/auth/*`).

---

## 1. Authentification

### POST /auth/login
Connexion d'un utilisateur.

**Body**
```json
{ "username": "pharmacien1", "password": "secret" }
```

**200 OK**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "pharmacien1",
    "full_name": "Eli Raz",
    "role": "pharmacien"
  }
}
```

**Rôles possibles** : `admin`, `pharmacien`, `patient`.

**Erreurs** : `401` si identifiants invalides.

### GET /auth/me
Retourne l'utilisateur courant (token valide requis).

**200 OK** — même objet `user` que ci-dessus.
**Erreurs** : `401` si token manquant/invalide.

---

## 2. Médicaments (rôle `pharmacien` et `admin`)

### GET /medicaments
Liste des médicaments.

**Query params** : `search?` (nom/composition), `categorie?`, `page?=1`, `limit?=50`

**200 OK**
```json
{
  "items": [
    {
      "id": 10,
      "nom": "Paracétamol 500mg",
      "categorie": "Antalgique",
      "prix": 1500,
      "quantite_stock": 120,
      "seuil_alerte": 20,
      "date_expiration": "2027-06-30",
      "fournisseur_id": 3
    }
  ],
  "total": 145,
  "page": 1
}
```

### GET /medicaments/{id}
Détail d'un médicament (même structure que ci-dessus).

### POST /medicaments
Création.

**Body**
```json
{
  "nom": "Ibuprofène 400mg",
  "categorie": "Antalgique",
  "prix": 2000,
  "quantite_stock": 80,
  "seuil_alerte": 15,
  "date_expiration": "2027-12-31",
  "fournisseur_id": 2
}
```
**200 OK** → objet créé. **Erreurs** : `422` validation, `409` doublon.

### PUT /medicaments/{id}
Mise à jour partielle (mêmes champs que POST, tous optionnels).
**200 OK** → objet mis à jour.

### DELETE /medicaments/{id}
Suppression. **204 No Content**.

---

## 3. Stock (rôle `pharmacien` et `admin`)

### GET /stock/ruptures
Médicaments en rupture ou sous le seuil d'alerte.

**200 OK**
```json
{
  "items": [
    { "id": 10, "nom": "Paracétamol", "quantite_stock": 12, "seuil_alerte": 20, "etat": "alerte" }
  ]
}
```
`etat` : `"alerte"` (sous le seuil) ou `"rupture"` (quantité = 0).

### POST /stock/ajout
Entrée de stock (réception livraison).

**Body**
```json
{ "medicament_id": 10, "quantite": 100 }
```
**200 OK** → `{ "id": 10, "quantite_stock": 220, "message": "Stock mis à jour" }`

### POST /stock/vente
Enregistrer une vente (décrémente le stock — surface niveau stock).

**Body**
```json
{ "medicament_id": 10, "quantite": 2, "client": "Patient X" }
```
**200 OK**
```json
{ "id": 10, "quantite_stock": 218, "vente_id": 55 }
```
**Erreurs** : `409` si stock insuffisant.

---

## 4. Recommandations IA (rôle `patient`, `pharmacien`)

### POST /ia/recommandations
L'IA étudie les symptômes saisis et renvoie des médicaments recommandés,
**en ne proposant que ceux disponibles en stock**.

**Body**
```json
{
  "symptomes": "fièvre, maux de tête, courbatures",
  "age": 34,
  "allergies": ["pénicilline"]
}
```

**200 OK**
```json
{
  "maladies_probables": [
    { "maladie": "Grippe", "probabilite": 0.82 },
    { "maladie": "Rhume", "probabilite": 0.15 }
  ],
  "recommandations": [
    {
      "medicament_id": 10,
      "nom": "Paracétamol 500mg",
      "categorie": "Antalgique",
      "prix": 1500,
      "disponible": true,
      "motif": "Relève la fièvre et soulage les céphalées"
    }
  ],
  "alerte": "Certains médicaments recommandés sont en rupture et ne sont pas affichés."
}
```

**Erreurs** : `422` si `symptomes` vide. `503` si le modèle IA n'est pas chargé.

---

## Codes d'erreur globaux
| Code | Signification |
|------|---------------|
| `401` | Non authentifié / token invalide |
| `403` | Rôle insuffisant pour la ressource |
| `404` | Ressource introuvable |
| `409` | Conflit (doublon, stock insuffisant) |
| `422` | Validation des données en échec |
| `503` | Service indisponible (modèle IA non chargé) |
