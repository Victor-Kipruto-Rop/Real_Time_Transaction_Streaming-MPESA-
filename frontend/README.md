# PesaGuard frontend workspaces

Six separately buildable JavaScript + Vite applications. Each lives in its own directory and can be deployed independently.

| Application | Directory | Intended host | Local container port |
|---|---|---|---:|
| PesaGuard Developer Platform | `frontend/developer-platform/` | `developers.pesaguard.co.ke` | 8401 |
| PesaGuard Workspace | `frontend/tenant-dashboard/` | `app.pesaguard.co.ke` | 8402 |
| PesaGuard Admin | `frontend/admin-dashboard/` | `admin.pesaguard.co.ke` | 8403 |
| PesaGuard | `frontend/public-website/` | `pesaguard.co.ke` | 8404 |
| PesaGuard Status | `frontend/status-website/` | `status.pesaguard.co.ke` | 8405 |
| PesaGuard Docs | `frontend/docs-website/` | `docs.pesaguard.co.ke` | 8406 |

## Local development

In each application directory:

```sh
npm install
npm run dev
npm run build
npm run preview
```

Build and run all six static containers from the repository root:

```sh
docker compose -f frontend/compose.yaml up -d --build
```

Set `VITE_API_BASE_URL` before building if the app needs an API base URL. Vite variables are embedded into browser assets and **must never contain secrets**. Do not put consumer secrets, API private keys, database URLs or signing keys in frontend env vars.

These are frontend starter implementations with independent layouts and navigation. Live API data, login/SSO, role-based authorization, tenant-aware routing, monitoring feeds, search and operational actions must be connected to real backend endpoints before production. Never fake health, verification or transaction status. Keep server authorization authoritative; hiding UI elements is not authorization.
