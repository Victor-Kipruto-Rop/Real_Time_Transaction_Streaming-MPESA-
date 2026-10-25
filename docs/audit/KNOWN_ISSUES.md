# Known Issues and Audit Follow-ups

This is a living engineering register. Severity reflects potential impact, not a claim that every item has been fully reproduced.

| ID | Severity | Finding / risk | Evidence | Required closure evidence | Status |
|---|---|---|---|---|---|
| AUD-001 | High | Callback trust model is unclear; custom JSON HMAC may be mistaken for provider authentication | `ingestion/webhook_receiver.py`, `app/config.py` | Document provider-supported trust controls; tests for each configured mode; no unsupported claims | Open |
| AUD-002 | High | Replay handling falls back to process-local memory when Redis is unavailable | `ingestion/webhook_receiver.py` | Explicit policy; production behavior tested with Redis down; multi-worker/multi-instance tests | Open |
| AUD-003 | High | Idempotency correctness depends on schema constraints and concurrency behavior | `app/database/idempotency.py` | Model/migration review plus concurrent duplicate test proving one durable accepted event | Open |
| AUD-004 | High | Callback processing code inspected does not itself demonstrate durable transaction persistence or event publication | `WebhookProcessor.process_c2b_confirmation` | End-to-end test asserting persisted event, published message and final state | Open |
| AUD-005 | High | Runtime entry points, Python versions, dependency sets and ports differ across Dockerfiles | `Dockerfile`, `Dockerfile.webhook`, Compose | One documented supported runtime; successful clean image builds and health checks | Open |
| AUD-006 | Medium | Compose PostgreSQL healthcheck had invalid quote syntax on hardening branch | `docker-compose.yml` | `docker compose config --quiet` passes in CI and clean environment | Fix committed; validation pending |
| AUD-007 | Medium | Empty password defaults may cause PostgreSQL container startup to fail unless environment is configured | Compose and `.env.example` | Fresh-clone setup guide and automated clean-start test | Open |
| AUD-008 | Medium | Test suite execution has not yet been recorded as baseline evidence | CI/test results not yet verified | CI run URL and pass/fail summary, including known failures | Open |
| AUD-009 | Medium | README production-readiness language may exceed verified runtime evidence | `README.md` | Align claims to measured/tested capabilities and document limitations | Open |
| AUD-010 | Medium | Replay/idempotency semantics may conflate a duplicate event with later callback/status events for the same transaction | `app/database/idempotency.py` | Define event identity versus transaction identity and test legitimate lifecycle updates | Open |

## Closure rules

- Do not mark an issue closed because code was merely added.
- Attach the relevant automated test, CI run, reproducible command output, or reviewed deployment evidence.
- If a behavior depends on external credentials or provider configuration, mark it as externally blocked and document the exact validation still required.
- Never include real M-Pesa customer data, production credentials, access tokens, or unredacted callback payloads in issue evidence.
