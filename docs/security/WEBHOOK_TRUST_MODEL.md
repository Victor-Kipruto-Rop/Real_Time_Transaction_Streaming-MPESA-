# Webhook Trust Model

## Purpose

This document separates payload validation, replay/idempotency controls, and sender authentication. These controls solve different problems and must not be presented as interchangeable.

## Current repository behavior

The inspected receiver canonicalizes JSON and can validate an HMAC-SHA256 signature using `WEBHOOK_SIGNING_SECRET`. It also checks a replay key using Redis when available and otherwise uses process-local memory, while calling a database idempotency helper.

The repository configuration currently allows signature enforcement to be disabled. A custom HMAC is meaningful only when the sender is known to possess the shared secret and the signing format is agreed out of band.

## Safaricom Daraja boundary

Do **not** assume that Safaricom Daraja sends the custom `X-Safaricom-Signature`, `X-Signature`, or `X-Mpesa-Signature` headers checked by this application. The code alone does not prove that these headers are provider-issued or cryptographically trustworthy. Confirm the supported provider integration and account configuration before relying on any provider-origin assertion.

If the provider callback mechanism does not provide a cryptographic signature, do not fabricate one or label an application-generated HMAC as Safaricom authentication. Use a documented layered control set appropriate to the provider, which may include HTTPS, strict schema/size validation, allowlisting only when provider IP ranges are officially documented and maintained, rate limits, anomaly monitoring, and transaction verification against an independent trusted source. Network source IP alone should not be treated as cryptographic proof.

## Required behavior by deployment mode

### Local development

- Use sandbox/synthetic events only.
- Clearly label custom HMAC as a local/test integration mechanism.
- Never expose development secrets or the receiver directly to the public internet.

### Production

- Explicitly configure the callback trust policy; avoid silently weakening it when Redis or another security dependency is unavailable.
- Separate authentication/trust validation from payload schema validation and idempotency.
- Reject oversized/malformed requests before expensive parsing or persistence.
- Redact phone numbers, credentials, passkeys, tokens and sensitive payload fields from logs.
- Return provider-compatible responses without claiming a transaction is reconciled or settled merely because a callback was received.
- Record a correlation ID and security outcome without storing secrets in logs.
- Require durable idempotency at the database boundary and define how legitimate later callback/status events are distinguished from duplicate delivery.
- Fail health/readiness checks or explicitly signal degraded protection when a required security dependency is unavailable.

## Acceptance tests

1. Missing or malformed required fields are rejected with the documented provider-compatible response.
2. Oversized bodies are rejected before full processing.
3. A configured custom-HMAC test sender is accepted only with the exact expected signature; tampering and missing signatures are rejected when enforcement is enabled.
4. The documentation clearly says this HMAC test mechanism does not prove Safaricom origin.
5. Redis unavailability produces the explicitly selected policy and visible degraded health; it must not silently imply distributed replay protection.
6. Concurrent identical deliveries create no duplicate durable transaction/event.
7. A legitimate later status/callback for the same transaction is not discarded solely because the transaction identifier was seen before.
8. Logs and error responses do not expose credentials or full sensitive payloads.
