# Frontend — Binôme 4 (Laryah, Joseph)

Interface **SvelteKit** (Svelte 5 + TypeScript) de la Gestion Pharmacie IA.
Le frontend consomme l'API FastAPI conforme au contrat dans [`docs/api-contrat.md`](../docs/api-contrat.md).

## Rôles & fonctionnalités

- **Pharmacien / Admin** (`/pharmacien`)
  - Dashboard : statistiques de stock, alertes et ruptures
  - Médicaments (`/pharmacien/medicaments`) : CRUD complet, recherche, ajout de stock, enregistrement de ventes
- **Patient / User** (`/patient`)
  - Saisie des symptômes (+ âge, allergies)
  - Recommandations IA : médicaments proposés **selon le stock disponible**, maladies probables

## Authentification

Login à `/login`. Le token JWT est stocké en `localStorage`.
Les routes sont protégées par rôle via `RoleGuard` (`src/lib/components/RoleGuard.svelte`).

## Structure

```
src/
├── lib/
│   ├── api/
│   │   ├── client.ts     # client fetch + gestion token + erreurs
│   │   └── types.ts      # types TS du contrat d'API
│   ├── components/
│   │   └── RoleGuard.svelte   # protection des routes par rôle
│   └── stores/
│       └── auth.ts       # état d'authentification (Svelte 5 runes)
└── routes/
    ├── login/            # page de connexion
    ├── pharmacien/       # dashboard + médcicaments (rôle pharmacien/admin)
    └── patient/          # symptômes + recommandations IA
```

## Lancement

```bash
cd frontend
npm install

npm run dev        # dev server (Vite)
npm run build      # compilation statique -> frontend/build/ (servie par FastAPI)
npm run check      # vérification de types Svelte
```

## Configuration API

L'URL de base de l'API est fixée à `http://localhost:8000` dans
`src/lib/api/client.ts` (à adapter selon déploiement).
