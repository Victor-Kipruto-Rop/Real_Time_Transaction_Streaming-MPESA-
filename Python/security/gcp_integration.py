"""
GCP Integration and Security Module
Handles secure connection to Google Cloud Platform, secrets management, and encryption
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import json
from datetime import datetime
import hashlib
import hmac

# GCP imports
try:
    from google.cloud import secretmanager
    from google.cloud import storage
    from google.auth import default

    HAS_GCP = True
except ImportError:
    HAS_GCP = False

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class GCPSecurityManager:
    """Manage GCP security and secrets"""

    def __init__(self):
        """Initialize GCP security manager"""
        self.project_id = os.getenv("GCP_PROJECT_ID", "mpesapipeline")
        self.region = os.getenv("GCP_REGION", "africa-south1")
        self.has_gcp = HAS_GCP

        if self.has_gcp:
            try:
                self.credentials, self.project = default()
                self.secret_client = secretmanager.SecretManagerServiceClient()
                self.storage_client = storage.Client()
                logger.info(f"Connected to GCP project: {self.project_id}")
            except Exception as e:
                logger.warning(f"GCP authentication failed: {e}")
                self.has_gcp = False

    def store_secret(self, secret_id: str, secret_value: str) -> bool:
        """Store secret in Google Secret Manager"""
        if not self.has_gcp:
            logger.error("GCP not available")
            return False

        try:
            parent = f"projects/{self.project_id}"

            # Check if secret exists
            try:
                self.secret_client.get_secret(
                    request={"name": f"{parent}/secrets/{secret_id}"}
                )
                # Add new version
                self.secret_client.add_secret_version(
                    request={
                        "parent": f"{parent}/secrets/{secret_id}",
                        "payload": {"data": secret_value.encode("UTF-8")},
                    }
                )
                logger.info(f"Updated secret: {secret_id}")
            except Exception:
                # Create new secret
                self.secret_client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {"replication": {"automatic": {}}},
                    }
                )
                self.secret_client.add_secret_version(
                    request={
                        "parent": f"{parent}/secrets/{secret_id}",
                        "payload": {"data": secret_value.encode("UTF-8")},
                    }
                )
                logger.info(f"Created secret: {secret_id}")

            return True
        except Exception as e:
            logger.error(f"Error storing secret: {e}")
            return False

    def retrieve_secret(self, secret_id: str) -> Optional[str]:
        """Retrieve secret from Google Secret Manager"""
        if not self.has_gcp:
            logger.warning("GCP not available, returning environment variable")
            return os.getenv(secret_id)

        try:
            parent = f"projects/{self.project_id}"
            name = f"{parent}/secrets/{secret_id}/versions/latest"
            response = self.secret_client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Error retrieving secret: {e}")
            return os.getenv(secret_id)

    def backup_to_gcs(
        self, local_file: str, bucket_name: str, remote_file: Optional[str] = None
    ) -> bool:
        """Backup file to Google Cloud Storage"""
        if not self.has_gcp:
            logger.error("GCP not available")
            return False

        try:
            if not os.path.exists(local_file):
                logger.error(f"File not found: {local_file}")
                return False

            bucket = self.storage_client.bucket(bucket_name)
            remote_name = remote_file or os.path.basename(local_file)
            blob = bucket.blob(f"backups/{datetime.utcnow().isoformat()}/{remote_name}")
            blob.upload_from_filename(local_file)

            logger.info(f"Backed up {local_file} to gs://{bucket_name}/{remote_name}")
            return True
        except Exception as e:
            logger.error(f"Backup error: {e}")
            return False


class SecurityHardeningManager:
    """Implement security hardening measures"""

    @staticmethod
    def generate_api_signature(secret: str, timestamp: str, payload: str) -> str:
        """Generate HMAC signature for API authentication"""
        message = f"{timestamp}{payload}".encode("utf-8")
        signature = hmac.new(
            secret.encode("utf-8"), message, hashlib.sha256
        ).hexdigest()
        return signature

    @staticmethod
    def validate_api_signature(
        secret: str, timestamp: str, payload: str, provided_signature: str
    ) -> bool:
        """Validate incoming API signature"""
        expected_signature = SecurityHardeningManager.generate_api_signature(
            secret, timestamp, payload
        )
        return hmac.compare_digest(expected_signature, provided_signature)

    @staticmethod
    def encrypt_field(value: str, key: str) -> str:
        """Encrypt sensitive field (basic encryption)"""
        try:
            from cryptography.fernet import Fernet

            cipher = Fernet(key)
            encrypted = cipher.encrypt(value.encode())
            return encrypted.decode()
        except Exception:
            logger.warning("Encryption not available, storing plaintext")
            return value

    @staticmethod
    def decrypt_field(encrypted_value: str, key: str) -> str:
        """Decrypt sensitive field"""
        try:
            from cryptography.fernet import Fernet

            cipher = Fernet(key)
            decrypted = cipher.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            return None

    @staticmethod
    def generate_encryption_key() -> str:
        """Generate new encryption key"""
        from cryptography.fernet import Fernet

        return Fernet.generate_key().decode()

    @staticmethod
    def sanitize_log_entry(entry: str) -> str:
        """Remove sensitive data from logs"""
        import re

        # Remove phone numbers
        entry = re.sub(r"\b\d{10,12}\b", "[PHONE_REDACTED]", entry)

        # Remove API keys
        entry = re.sub(r"[A-Za-z0-9]{40,}", "[KEY_REDACTED]", entry)

        # Remove amounts (sometimes sensitive)
        entry = re.sub(r'"amount":\s*[\d.]+', '"amount": [AMOUNT_REDACTED]', entry)

        # Remove emails
        entry = re.sub(r"[\w\.-]+@[\w\.-]+\.\w+", "[EMAIL_REDACTED]", entry)

        return entry


class SecurityPolicies:
    """Define and enforce security policies"""

    @staticmethod
    def get_security_headers() -> Dict[str, str]:
        """Get recommended security headers for API"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
        }

    @staticmethod
    def get_rate_limits() -> Dict[str, Dict[str, int]]:
        """Define rate limiting policies"""
        return {
            "api_endpoint": {
                "requests_per_minute": 100,
                "requests_per_hour": 5000,
                "requests_per_day": 100000,
            },
            "webhook": {
                "requests_per_minute": 500,
                "requests_per_hour": 30000,
                "requests_per_day": 500000,
            },
            "admin_endpoint": {
                "requests_per_minute": 10,
                "requests_per_hour": 1000,
                "requests_per_day": 10000,
            },
        }

    @staticmethod
    def get_authentication_policies() -> Dict[str, Any]:
        """Define authentication policies"""
        return {
            "token_expiry_hours": 24,
            "refresh_token_expiry_days": 30,
            "max_failed_attempts": 5,
            "lockout_duration_minutes": 15,
            "password_min_length": 12,
            "require_mfa": True,
            "allowed_origins": [
                "https://chamayangu.online",
                "https://api.chamayangu.online",
            ],
            "jwt_algorithm": "HS256",
        }

    @staticmethod
    def get_encryption_policies() -> Dict[str, Any]:
        """Define encryption policies"""
        return {
            "tls_version": "TLSv1.3",
            "cipher_suites": [
                "TLS_AES_256_GCM_SHA384",
                "TLS_CHACHA20_POLY1305_SHA256",
                "TLS_AES_128_GCM_SHA256",
            ],
            "certificate_validity_days": 365,
            "encrypt_at_rest": True,
            "encrypt_in_transit": True,
            "key_rotation_days": 90,
        }

    @staticmethod
    def get_audit_logging_policies() -> Dict[str, Any]:
        """Define audit logging policies"""
        return {
            "log_authentication_events": True,
            "log_data_access": True,
            "log_api_calls": True,
            "log_admin_actions": True,
            "retention_days": 90,
            "real_time_alerting": True,
            "alert_on_suspicious_activity": True,
            "sensitive_data_masking": True,
        }

    @staticmethod
    def get_network_policies() -> Dict[str, Any]:
        """Define network security policies"""
        return {
            "firewall_enabled": True,
            "ip_whitelist_enabled": True,
            "ddos_protection": True,
            "vpc_enabled": True,
            "nat_gateway": True,
            "private_subnet": True,
            "allowed_cidr_blocks": ["10.0.0.0/8"],
            "blocked_countries": [],
        }


class GCPIntegrationManager:
    """Manage GCP Cloud SQL integration"""

    def __init__(self):
        """Initialize GCP integration"""
        self.project_id = os.getenv("GCP_PROJECT_ID", "mpesapipeline")
        self.instance_name = os.getenv("GCP_SQL_INSTANCE", "mpesa-postgres")
        self.db_name = os.getenv("DB_NAME", "mpesa_analytics")
        self.region = os.getenv("GCP_REGION", "africa-south1")
        self.has_gcp = HAS_GCP

    def get_cloud_sql_connection_string(self) -> str:
        """Get Cloud SQL connection string"""
        return (
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{self.project_id}:{self.region}:{self.instance_name}/{self.db_name}"
        )

    def get_deployment_config(self) -> Dict[str, Any]:
        """Get GCP deployment configuration"""
        return {
            "compute": {
                "platform": "Cloud Run",
                "memory": "2Gi",
                "cpu": "2",
                "timeout_seconds": 3600,
                "concurrency": 100,
                "max_instances": 100,
                "min_instances": 1,
            },
            "database": {
                "platform": "Cloud SQL",
                "instance": self.instance_name,
                "database": self.db_name,
                "region": self.region,
                "tier": "db-custom-4-16384",
                "backup_location": f"gs://{self.project_id}-backups",
                "automated_backups": True,
                "backup_retention_days": 30,
            },
            "cache": {
                "platform": "Cloud Memorystore",
                "memory_size_gb": 5,
                "tier": "standard",
                "region": self.region,
            },
            "message_queue": {
                "platform": "Cloud Pub/Sub",
                "topic": "mpesa-transactions",
                "subscription": "mpesa-consumer",
            },
            "storage": {
                "platform": "Cloud Storage",
                "bucket": f"{self.project_id}-data",
                "versioning": True,
            },
            "monitoring": {
                "platform": "Cloud Monitoring",
                "alerting": True,
                "log_retention_days": 30,
            },
        }

    def get_migration_steps(self) -> Dict[str, str]:
        """Get steps to migrate to GCP"""
        return {
            "step_1": "Create Cloud SQL instance (4 vCPU, 16GB RAM)",
            "step_2": "Create VPC network for isolation",
            "step_3": "Create Cloud Storage bucket for backups",
            "step_4": "Configure Cloud SQL Auth Proxy",
            "step_5": "Migrate database from localhost to Cloud SQL",
            "step_6": "Update .env with Cloud SQL connection string",
            "step_7": "Create Cloud Pub/Sub topic and subscription",
            "step_8": "Deploy application to Cloud Run",
            "step_9": "Configure Cloud Load Balancer",
            "step_10": "Setup Cloud Monitoring and alerting",
        }


def print_security_summary():
    """Print security summary"""
    print("\n" + "=" * 80)
    print("GCP SECURITY & INTEGRATION CONFIGURATION")
    print("=" * 80)

    print("\n📋 SECURITY POLICIES:")
    for header, config in [
        ("Rate Limiting", SecurityPolicies.get_rate_limits()),
        ("Authentication", SecurityPolicies.get_authentication_policies()),
        ("Encryption", SecurityPolicies.get_encryption_policies()),
        ("Audit Logging", SecurityPolicies.get_audit_logging_policies()),
        ("Network", SecurityPolicies.get_network_policies()),
    ]:
        print(f"\n{header}:")
        print(json.dumps(config, indent=2))

    print("\n📦 GCP DEPLOYMENT CONFIG:")
    manager = GCPIntegrationManager()
    print(json.dumps(manager.get_deployment_config(), indent=2))

    print("\n🔄 MIGRATION STEPS:")
    for step, description in manager.get_migration_steps().items():
        print(f"  {step}: {description}")

    print("\n🔒 SECURITY HEADERS:")
    for header, value in SecurityPolicies.get_security_headers().items():
        print(f"  {header}: {value}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    print_security_summary()
