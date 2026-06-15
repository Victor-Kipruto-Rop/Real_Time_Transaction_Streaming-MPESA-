#!/usr/bin/env python3
import os
import base64
from dotenv import dotenv_values

def generate_k8s_resources():
    env_vars = dotenv_values(".env")
    
    # Generate Secrets
    secrets_content = f"""---
apiVersion: v1
kind: Secret
metadata:
  name: daraja-credentials
  namespace: mpesa-pipeline
type: Opaque
stringData:
  api-key: "{env_vars.get('DARAJA_CONSUMER_KEY', '')}"
  api-secret: "{env_vars.get('DARAJA_CONSUMER_SECRET', '')}"
  passkey: "{env_vars.get('DARAJA_PASSKEY', '')}"

---
apiVersion: v1
kind: Secret
metadata:
  name: db-credentials
  namespace: mpesa-pipeline
type: Opaque
stringData:
  username: "{env_vars.get('POSTGRES_USER', '')}"
  password: "{env_vars.get('POSTGRES_PASSWORD', '')}"
  host: "{env_vars.get('POSTGRES_HOST', '')}"
  database: "{env_vars.get('POSTGRES_DB', '')}"

---
apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: mpesa-pipeline
type: Opaque
stringData:
  access-key-id: "{env_vars.get('AWS_ACCESS_KEY_ID', '')}"
  secret-access-key: "{env_vars.get('AWS_SECRET_ACCESS_KEY', '')}"
  region: "{env_vars.get('AWS_REGION', '')}"

---
apiVersion: v1
kind: Secret
metadata:
  name: ui-security
  namespace: mpesa-pipeline
type: Opaque
stringData:
  ui-token: "{env_vars.get('UI_TOKEN', '')}"
"""

    with open("kubernetes/secrets.generated.yaml", "w") as f:
        f.write(secrets_content)
    print("✓ Created kubernetes/secrets.generated.yaml")

    # Generate ConfigMap
    configmap_content = f"""---
apiVersion: v1
kind: ConfigMap
metadata:
  name: mpesa-config
  namespace: mpesa-pipeline
data:
  ENVIRONMENT: "{env_vars.get('DARAJA_ENVIRONMENT', 'sandbox')}"
  KAFKA_BROKERS: "{env_vars.get('KAFKA_BROKERS', 'localhost:9092')}"
  KAFKA_TOPIC_TRANSACTIONS: "{env_vars.get('KAFKA_TOPIC_TRANSACTIONS', 'mpesa-transactions')}"
  REDIS_HOST: "{env_vars.get('REDIS_HOST', 'localhost')}"
  REDIS_PORT: "{env_vars.get('REDIS_PORT', '6379')}"
  DOMAIN: "{env_vars.get('DOMAIN', 'your-domain.com')}"
  PUBLIC_BASE_URL: "{env_vars.get('PUBLIC_BASE_URL', 'https://your-domain.com')}"
"""

    with open("kubernetes/configmap.generated.yaml", "w") as f:
        f.write(configmap_content)
    print("✓ Created kubernetes/configmap.generated.yaml")

if __name__ == "__main__":
    generate_k8s_resources()
