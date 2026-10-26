# PesaGuard

Independent JavaScript + Vite application for `pesaguard.co.ke`.

## Run

```sh
npm install
npm run dev
npm run build
npm run preview
```

Copy `.env.example` to `.env.local` and set `VITE_API_BASE_URL` for your development API. Vite environment variables are public client-side configuration; never place secrets in them.

## Production integration gates

- Connect real backend APIs and authenticated session flows.
- Enforce authorization, tenant scope and privileged actions on the server.
- Add accessible error, loading, empty and retry states for API operations.
- Configure CSP, TLS, secure session strategy, security headers, logging, analytics/privacy choices and deployment health checks.
- Do not display fabricated transaction metrics, verification results or service status. 
