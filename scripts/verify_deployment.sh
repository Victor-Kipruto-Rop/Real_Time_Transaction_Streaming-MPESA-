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
