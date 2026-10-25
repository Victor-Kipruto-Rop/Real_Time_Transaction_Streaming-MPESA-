#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${BASE_URL:-http://localhost:5000}"
command -v curl >/dev/null || { echo "curl is required" >&2; exit 127; }
response="$(curl --fail --silent --show-error --max-time 5 "$BASE_URL/ready")"
python - "$response" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
if payload.get("status") != "ready" or payload.get("database") != "ok":
    raise SystemExit(f"service is not ready: {payload}")
print(json.dumps(payload, indent=2, sort_keys=True))
PY

metrics="$(curl --fail --silent --show-error --max-time 5 "$BASE_URL/metrics")"
if ! grep -q 'mpesa_outbox_events' <<< "$metrics"; then
  echo "Prometheus outbox metrics were not found" >&2
  exit 1
fi
echo "Prometheus outbox metrics endpoint is responding."

if [[ "${RUN_SYNTHETIC_SMOKE:-0}" == "1" ]]; then
  command -v psql >/dev/null || { echo "psql is required for the synthetic smoke check" >&2; exit 127; }
  PGHOST="${PGHOST:-${POSTGRES_HOST:-localhost}}"
  PGPORT="${PGPORT:-${POSTGRES_PORT:-5433}}"
  PGDATABASE="${PGDATABASE:-${POSTGRES_DB:-mpesa_analytics}}"
  PGUSER="${PGUSER:-${POSTGRES_USER:-data_engineer}}"
  export PGHOST PGPORT PGDATABASE PGUSER
  : "${PGPASSWORD:?Set PGPASSWORD for the synthetic smoke check}"
  transaction_id="SMOKE-$(date -u +%Y%m%dT%H%M%SZ)-$$"
  payload="$(python - "$transaction_id" <<'PY'
import json
import sys
from datetime import datetime, timezone
print(json.dumps({
    "TransID": sys.argv[1],
    "TransAmount": "10",
    "MSISDN": "254712345678",
    "TransTime": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    "AccountReference": "SYNTHETIC-DEPLOYMENT-CHECK",
}))
PY
)"
  callback_response="$(curl --fail --silent --show-error --max-time 10 \
    -H 'Content-Type: application/json' -d "$payload" \
    "$BASE_URL/webhook/c2b/confirmation")"
  python - "$callback_response" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
if payload.get("ResultCode") != 0:
    raise SystemExit(f"synthetic callback was not accepted: {payload}")
PY
  for attempt in $(seq 1 60); do
    outbox_status="$(psql -X -A -t -c "SELECT status FROM event_outbox WHERE event_type='c2b_confirmation' AND payload->>'transaction_id'='$transaction_id' ORDER BY id DESC LIMIT 1" | tr -d '[:space:]')"
    callback_count="$(psql -X -A -t -c "SELECT COUNT(*) FROM mpesa_callback_events WHERE payload->>'transaction_id'='$transaction_id'" | tr -d '[:space:]')"
    transaction_count="$(psql -X -A -t -c "SELECT COUNT(*) FROM mpesa_transactions_raw WHERE transaction_id='$transaction_id'" | tr -d '[:space:]')"
    if [[ "$outbox_status" == "published" && "$callback_count" == "1" && "$transaction_count" == "1" ]]; then
      echo "Synthetic callback reached Kafka and PostgreSQL: $transaction_id"
      exit 0
    fi
    sleep 1
  done
  echo "Synthetic callback did not complete within 60 seconds: id=$transaction_id outbox=$outbox_status callback_rows=$callback_count transaction_rows=$transaction_count" >&2
  exit 1
fi
