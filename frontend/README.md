# PesaGuard frontend workspaces

Six separately buildable JavaScript + Vite applications. Each lives in its own directory and can be deployed independently.

| Application | Directory | Intended host |
|---|---|---|
| PesaGuard Developer Platform | `frontend/developer-platform/` | `developers.pesaguard.co.ke` |
| PesaGuard Workspace | `frontend/tenant-dashboard/` | `app.pesaguard.co.ke` |
| PesaGuard Admin | `frontend/admin-dashboard/` | `admin.pesaguard.co.ke` |
| PesaGuard | `frontend/public-website/` | `pesaguard.co.ke` |
| PesaGuard Status | `frontend/status-website/` | `status.pesaguard.co.ke` |
| PesaGuard Docs | `frontend/docs-website/` | `docs.pesaguard.co.ke` |

## Local development

In each application directory:

```sh
npm install
npm run dev
npm run build
npm run preview
```

Set `VITE_API_BASE_URL` in a local `.env.local` to the appropriate public API URL. Vite variables are embedded into browser assets and **must never contain secrets**. Do not put consumer secrets, API private keys, database URLs or signing keys in frontend env vars.

These are frontend starter implementations with independent layouts and navigation. Live API data, login/SSO, role-based authorization, tenant-aware routing, monitoring feeds, search and operational actions must be connected to real backend endpoints before production. Never fake health, verification or transaction status. Keep server authorization authoritative; hiding UI elements is not authorization.
