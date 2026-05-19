"""Normalize EC2 .env values for Docker Compose runtime.

The local .env may use host-facing addresses such as localhost. Containers need
Docker service names instead. This script preserves secret values while forcing
the runtime endpoints that must match the compose stack.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


ENV_PATH = Path(".env")
FALLBACK_PUBLIC_BASE_URL = "http://54.193.78.115"


def parse_env(path: Path) -> tuple[dict[str, str], list[str]]:
    data: dict[str, str] = {}
    lines = path.read_text().splitlines() if path.exists() else []
    for raw in lines:
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        data[key.strip()] = value.strip()
    return data, lines


def write_env(path: Path, data: dict[str, str], original_lines: list[str]) -> None:
    seen: set[str] = set()
    output: list[str] = []
    for raw in original_lines:
        stripped = raw.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            output.append(raw)
            continue
        if "=" not in raw:
            continue
        key = raw.split("=", 1)[0].strip()
        if key in data and key not in seen:
            output.append(f"{key}={data[key]}")
            seen.add(key)

    for key in sorted(data):
        if key not in seen:
            output.append(f"{key}={data[key]}")

    path.write_text("\n".join(output) + "\n")
    path.chmod(0o600)


def alter_postgres_password(password: str) -> None:
    if not password:
        return
    escaped = password.replace("'", "''")
    sql = f"ALTER USER data_engineer WITH PASSWORD '{escaped}';\n"
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "mpesa_postgres",
            "psql",
            "-U",
            "data_engineer",
            "-d",
            "mpesa_analytics",
        ],
        input=sql,
        text=True,
        check=True,
    )


def get_public_base_url(data: dict[str, str]) -> str:
    configured = data.get("PUBLIC_BASE_URL") or data.get("APP_PUBLIC_BASE_URL")
    if configured:
        return configured.rstrip("/")

    domain = data.get("DOMAIN") or data.get("APP_DOMAIN")
    if domain and domain not in {"localhost", "localhost:8000"}:
        if domain.startswith(("http://", "https://")):
            return domain.rstrip("/")
        return f"https://{domain.strip('/')}"

    return FALLBACK_PUBLIC_BASE_URL


def should_replace_url(current: str, public_base_url: str) -> bool:
    if not current:
        return True
    stale_markers = ("example.com", "localhost", "127.0.0.1", ":5000")
    if any(marker in current for marker in stale_markers):
        return True
    if current.startswith(FALLBACK_PUBLIC_BASE_URL) and current != public_base_url:
        return True
    return not current.startswith(public_base_url)


def main() -> None:
    data, original_lines = parse_env(ENV_PATH)
    public_base_url = get_public_base_url(data)
    data["PUBLIC_BASE_URL"] = public_base_url
    if data.get("MPESA_BUSINESS_SHORTCODE"):
        data.setdefault("DARAJA_BUSINESS_SHORTCODE", data["MPESA_BUSINESS_SHORTCODE"])
        data.setdefault("DARAJA_SHORTCODE", data["MPESA_BUSINESS_SHORTCODE"])
        data.setdefault("DARAJA_C2B_SHORTCODE", data["MPESA_BUSINESS_SHORTCODE"])
    if data.get("DARAJA_SHORTCODE"):
        data.setdefault("DARAJA_BUSINESS_SHORTCODE", data["DARAJA_SHORTCODE"])
        data.setdefault("DARAJA_C2B_SHORTCODE", data["DARAJA_SHORTCODE"])
        data.setdefault("MPESA_BUSINESS_SHORTCODE", data["DARAJA_SHORTCODE"])
    if data.get("MPESA_PASSKEY"):
        data.setdefault("DARAJA_PASSKEY", data["MPESA_PASSKEY"])
    if data.get("DARAJA_PASSKEY"):
        data.setdefault("MPESA_PASSKEY", data["DARAJA_PASSKEY"])
    data.setdefault("DARAJA_RESPONSE_TYPE", "Completed")

    data.update(
        {
            "POSTGRES_HOST": "postgres",
            "POSTGRES_PORT": "5432",
            "POSTGRES_DB": "mpesa_analytics",
            "POSTGRES_USER": "data_engineer",
            "KAFKA_BROKERS": "kafka:29092",
            "REDIS_HOST": "redis",
            "REDIS_PORT": "6379",
            "GRAFANA_HOST_PORT": data.get("GRAFANA_HOST_PORT") or "3000",
        }
    )

    callback = data.get("CALLBACK_URL", "")
    if should_replace_url(callback, public_base_url):
        data["CALLBACK_URL"] = f"{public_base_url}/webhook/stk/callback"

    callback_map = {
        "DARAJA_VALIDATION_URL": f"{public_base_url}/webhook/c2b/validation",
        "DARAJA_CONFIRMATION_URL": f"{public_base_url}/webhook/c2b/confirmation",
        "DARAJA_B2C_RESULT_URL": f"{public_base_url}/webhook/b2c/result",
        "DARAJA_B2C_TIMEOUT_URL": f"{public_base_url}/webhook/b2c/result",
        "DARAJA_STK_CALLBACK_URL": data["CALLBACK_URL"],
        "C2B_VALIDATION_URL": f"{public_base_url}/webhook/c2b/validation",
        "C2B_CONFIRMATION_URL": f"{public_base_url}/webhook/c2b/confirmation",
    }
    for key, value in callback_map.items():
        current = data.get(key, "")
        if should_replace_url(current, public_base_url):
            data[key] = value

    grafana_url = data.get("GRAFANA_URL", "")
    if not grafana_url or "localhost" in grafana_url or ":3000" in grafana_url:
        data["GRAFANA_URL"] = "http://54.193.78.115/grafana"
    data["GRAFANA_SERVE_FROM_SUB_PATH"] = "true"

    write_env(ENV_PATH, data, original_lines)
    alter_postgres_password(data.get("POSTGRES_PASSWORD", ""))
    print("ENV_NORMALIZED")


if __name__ == "__main__":
    main()
