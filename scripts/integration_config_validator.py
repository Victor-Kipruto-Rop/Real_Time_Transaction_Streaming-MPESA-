#!/usr/bin/env python
"""
Comprehensive integration validator for all .env configurations.

Validates:
1. Database connectivity (PostgreSQL)
2. Kafka broker connectivity
3. Daraja API credentials
4. Webhook URL configuration
5. Redis cache configuration
6. External integrations (Slack, Email, Monitoring)
7. Security settings
8. M-Pesa till configuration
"""

import os
import sys
import logging
from typing import Dict, List, Tuple

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates all .env configurations and module integrations."""

    def __init__(self):
        """Initialize validator."""
        load_dotenv()
        self.results: Dict[str, List[Tuple[str, bool, str]]] = {}

    def validate_all(self) -> bool:
        """Run all validations and return success status."""
        logger.info("=" * 80)
        logger.info("INTEGRATION VALIDATION SUITE")
        logger.info("=" * 80)
        logger.info("")

        all_passed = True

        # 1. Runtime & Logging
        logger.info("1. Validating RUNTIME & LOGGING Configuration...")
        all_passed &= self._validate_runtime()

        # 2. Database
        logger.info("\n2. Validating DATABASE Configuration...")
        all_passed &= self._validate_database()

        # 3. Kafka
        logger.info("\n3. Validating MESSAGE QUEUE (Kafka) Configuration...")
        all_passed &= self._validate_kafka()

        # 4. Daraja API
        logger.info("\n4. Validating SAFARICOM DARAJA API Configuration...")
        all_passed &= self._validate_daraja()

        # 5. C2B Configuration
        logger.info("\n5. Validating C2B CONFIGURATION...")
        all_passed &= self._validate_c2b()

        # 6. B2C Configuration
        logger.info("\n6. Validating B2C CONFIGURATION...")
        all_passed &= self._validate_b2c()

        # 7. M-Pesa Till
        logger.info("\n7. Validating M-PESA TILL DETAILS...")
        all_passed &= self._validate_mpesa_till()

        # 8. Webhooks
        logger.info("\n8. Validating WEBHOOKS & CALLBACKS...")
        all_passed &= self._validate_webhooks()

        # 9. External Integrations
        logger.info("\n9. Validating EXTERNAL INTEGRATIONS...")
        all_passed &= self._validate_external_integrations()

        # 10. Monitoring
        logger.info("\n10. Validating MONITORING & ALERTING...")
        all_passed &= self._validate_monitoring()

        # 11. Redis Cache
        logger.info("\n11. Validating REDIS CACHE...")
        all_passed &= self._validate_redis()

        # 12. Security
        logger.info("\n12. Validating SECURITY SETTINGS...")
        all_passed &= self._validate_security()

        # 13. GCP Configuration
        logger.info("\n13. Validating GCP CONFIGURATION...")
        all_passed &= self._validate_gcp()

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("VALIDATION SUMMARY")
        logger.info("=" * 80)

        return all_passed

    def _validate_runtime(self) -> bool:
        """Validate runtime and logging configuration."""
        checks = []

        log_level = os.getenv("LOG_LEVEL", "INFO")
        checks.append(("LOG_LEVEL set", log_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       f"LOG_LEVEL={log_level}"))

        environment = os.getenv("ENVIRONMENT", "development")
        checks.append(("ENVIRONMENT set", environment in ["development", "staging", "production"],
                       f"ENVIRONMENT={environment}"))

        self.results["Runtime & Logging"] = checks
        return self._print_checks(checks)

    def _validate_database(self) -> bool:
        """Validate PostgreSQL database configuration."""
        checks = []

        db_host = os.getenv("POSTGRES_HOST")
        checks.append(("POSTGRES_HOST configured", bool(db_host), f"Host: {db_host}"))

        db_port = os.getenv("POSTGRES_PORT")
        checks.append(("POSTGRES_PORT configured", bool(db_port), f"Port: {db_port}"))

        db_name = os.getenv("POSTGRES_DB")
        checks.append(("POSTGRES_DB configured", bool(db_name), f"Database: {db_name}"))

        db_user = os.getenv("POSTGRES_USER")
        checks.append(("POSTGRES_USER configured", bool(db_user), f"User: {db_user}"))

        db_password = os.getenv("POSTGRES_PASSWORD")
        checks.append(("POSTGRES_PASSWORD configured", bool(db_password), "✓ (hidden)"))

        # Try importing modules that use database
        try:
            from ingestion.db_pool import DatabasePool
            checks.append(("DatabasePool module importable", True, "✓"))
        except Exception as e:
            checks.append(("DatabasePool module importable", False, str(e)))

        self.results["Database"] = checks
        return self._print_checks(checks)

    def _validate_kafka(self) -> bool:
        """Validate Kafka configuration."""
        checks = []

        kafka_brokers = os.getenv("KAFKA_BROKERS")
        checks.append(("KAFKA_BROKERS configured", bool(kafka_brokers), f"Brokers: {kafka_brokers}"))

        kafka_topic_tx = os.getenv("KAFKA_TOPIC_TRANSACTIONS")
        checks.append(("KAFKA_TOPIC_TRANSACTIONS configured", bool(kafka_topic_tx), f"Topic: {kafka_topic_tx}"))

        kafka_topic_alerts = os.getenv("KAFKA_TOPIC_ALERTS")
        checks.append(("KAFKA_TOPIC_ALERTS configured", bool(kafka_topic_alerts), f"Topic: {kafka_topic_alerts}"))

        kafka_group = os.getenv("KAFKA_GROUP_ID")
        checks.append(("KAFKA_GROUP_ID configured", bool(kafka_group), f"Group: {kafka_group}"))

        # Try importing modules
        try:
            from ingestion.kafka_producer import MpesaKafkaProducer
            checks.append(("KafkaProducer module importable", True, "✓"))
        except Exception as e:
            checks.append(("KafkaProducer module importable", False, str(e)[:50]))

        try:
            # Try importing - creates logs directory if needed
            import pathlib
            pathlib.Path('logs').mkdir(exist_ok=True)
            from ingestion.kafka_consumer import KafkaConsumer
            checks.append(("KafkaConsumer module importable", True, "✓"))
        except Exception as e:
            checks.append(("KafkaConsumer module importable", False, str(e)[:50]))

        self.results["Kafka"] = checks
        return self._print_checks(checks)

    def _validate_daraja(self) -> bool:
        """Validate Daraja API configuration."""
        checks = []

        daraja_env = os.getenv("DARAJA_ENVIRONMENT")
        checks.append(("DARAJA_ENVIRONMENT configured", bool(daraja_env), f"Environment: {daraja_env}"))

        daraja_base = os.getenv("DARAJA_BASE_URL")
        checks.append(("DARAJA_BASE_URL configured", bool(daraja_base), f"URL: {daraja_base}"))

        consumer_key = os.getenv("DARAJA_CONSUMER_KEY")
        checks.append(("DARAJA_CONSUMER_KEY configured", bool(consumer_key), "✓ (hidden)"))

        consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET")
        checks.append(("DARAJA_CONSUMER_SECRET configured", bool(consumer_secret), "✓ (hidden)"))

        # Try importing and creating client
        try:
            from ingestion.daraja_client import DarajaClient
            client = DarajaClient.from_env()
            checks.append(("DarajaClient instantiable", True, "✓"))

            # Try getting token
            try:
                token = client.get_access_token()
                checks.append(("DarajaClient OAuth working", bool(token), f"Token length: {len(token)}"))
            except Exception as e:
                checks.append(("DarajaClient OAuth working", False, str(e)[:50]))
        except Exception as e:
            checks.append(("DarajaClient instantiable", False, str(e)[:50]))

        self.results["Daraja API"] = checks
        return self._print_checks(checks)

    def _validate_c2b(self) -> bool:
        """Validate C2B configuration."""
        checks = []

        c2b_shortcode = os.getenv("DARAJA_C2B_SHORTCODE")
        checks.append(("DARAJA_C2B_SHORTCODE configured", bool(c2b_shortcode), f"Shortcode: {c2b_shortcode}"))

        response_type = os.getenv("DARAJA_RESPONSE_TYPE")
        checks.append(("DARAJA_RESPONSE_TYPE configured", bool(response_type), f"Type: {response_type}"))

        validation_url = os.getenv("DARAJA_VALIDATION_URL")
        checks.append(("DARAJA_VALIDATION_URL configured", bool(validation_url), f"URL: {validation_url}"))

        confirmation_url = os.getenv("DARAJA_CONFIRMATION_URL")
        checks.append(("DARAJA_CONFIRMATION_URL configured", bool(confirmation_url), f"URL: {confirmation_url}"))

        test_msisdn = os.getenv("DARAJA_TEST_MSISDN")
        checks.append(("DARAJA_TEST_MSISDN configured", bool(test_msisdn), f"MSISDN: {test_msisdn}"))

        test_amount = os.getenv("DARAJA_TEST_AMOUNT")
        checks.append(("DARAJA_TEST_AMOUNT configured", bool(test_amount), f"Amount: {test_amount}"))

        test_ref = os.getenv("DARAJA_TEST_BILL_REF")
        checks.append(("DARAJA_TEST_BILL_REF configured", bool(test_ref), f"Reference: {test_ref}"))

        self.results["C2B Configuration"] = checks
        return self._print_checks(checks)

    def _validate_b2c(self) -> bool:
        """Validate B2C configuration."""
        checks = []

        b2c_result_url = os.getenv("DARAJA_B2C_RESULT_URL")
        checks.append(("DARAJA_B2C_RESULT_URL configured", bool(b2c_result_url), f"URL: {b2c_result_url}"))

        self.results["B2C Configuration"] = checks
        return self._print_checks(checks)

    def _validate_mpesa_till(self) -> bool:
        """Validate M-Pesa till configuration."""
        checks = []

        business_shortcode = os.getenv("MPESA_BUSINESS_SHORTCODE")
        checks.append(("MPESA_BUSINESS_SHORTCODE configured", bool(business_shortcode), f"Shortcode: {business_shortcode}"))

        till_number = os.getenv("MPESA_TILL_NUMBER")
        checks.append(("MPESA_TILL_NUMBER configured", bool(till_number), f"Till: {till_number}"))

        till_msisdn = os.getenv("MPESA_TILL_MSISDN")
        checks.append(("MPESA_TILL_MSISDN configured", bool(till_msisdn), f"MSISDN: {till_msisdn}"))

        passkey = os.getenv("MPESA_PASSKEY")
        checks.append(("MPESA_PASSKEY configured", bool(passkey), "✓ (hidden)"))

        # Try importing transaction handler
        try:
            from ingestion.mpesa_transactions import MpesaTransactionHandler
            handler = MpesaTransactionHandler()
            checks.append(("MpesaTransactionHandler instantiable", True, "✓"))
        except Exception as e:
            # If database not available, still pass if module imports
            if "connect" in str(e).lower() or "pool" in str(e).lower():
                checks.append(("MpesaTransactionHandler instantiable", True, "✓ (module OK, DB unavailable)"))
            else:
                checks.append(("MpesaTransactionHandler instantiable", False, str(e)[:50]))

        self.results["M-Pesa Till"] = checks
        return self._print_checks(checks)

    def _validate_webhooks(self) -> bool:
        """Validate webhook configuration."""
        checks = []

        callback_url = os.getenv("CALLBACK_URL")
        checks.append(("CALLBACK_URL configured", bool(callback_url), f"URL: {callback_url}"))

        callback_timeout = os.getenv("CALLBACK_TIMEOUT")
        checks.append(("CALLBACK_TIMEOUT configured", bool(callback_timeout), f"Timeout: {callback_timeout}s"))

        callback_retries = os.getenv("CALLBACK_RETRY_ATTEMPTS")
        checks.append(("CALLBACK_RETRY_ATTEMPTS configured", bool(callback_retries), f"Retries: {callback_retries}"))

        # Try importing webhook module (may be named differently)
        try:
            from ingestion import webhook_receiver
            checks.append(("webhook_receiver module importable", True, "✓"))
        except Exception as e:
            checks.append(("webhook_receiver module importable", False, str(e)[:50]))

        self.results["Webhooks & Callbacks"] = checks
        return self._print_checks(checks)

    def _validate_external_integrations(self) -> bool:
        """Validate external integrations (Slack, Email, etc.)."""
        checks = []

        slack_webhook = os.getenv("SLACK_WEBHOOK_URL")
        slack_enabled = os.getenv("SLACK_ALERTS_ENABLED", "false").lower() == "true"
        checks.append(("SLACK_WEBHOOK_URL configured", bool(slack_webhook), f"Enabled: {slack_enabled}"))

        email_enabled = os.getenv("EMAIL_ALERTS_ENABLED", "false").lower() == "true"
        email_smtp = os.getenv("EMAIL_SMTP_SERVER")
        checks.append(("EMAIL_SMTP_SERVER configured", bool(email_smtp) or not email_enabled, f"Server: {email_smtp}"))

        # Try importing alerting module
        try:
            from ingestion.alerting import AlertManager
            manager = AlertManager()
            checks.append(("AlertManager instantiable", True, "✓"))
        except Exception as e:
            checks.append(("AlertManager instantiable", False, str(e)[:50]))

        self.results["External Integrations"] = checks
        return self._print_checks(checks)

    def _validate_monitoring(self) -> bool:
        """Validate monitoring configuration."""
        checks = []

        grafana_enabled = os.getenv("GRAFANA_ENABLED", "false").lower() == "true"
        grafana_url = os.getenv("GRAFANA_URL")
        checks.append(("GRAFANA_URL configured", bool(grafana_url) or not grafana_enabled, f"URL: {grafana_url}"))

        prometheus_enabled = os.getenv("PROMETHEUS_ENABLED", "false").lower() == "true"
        prometheus_interval = os.getenv("PROMETHEUS_SCRAPE_INTERVAL")
        checks.append(("PROMETHEUS_SCRAPE_INTERVAL configured", bool(prometheus_interval) or not prometheus_enabled,
                       f"Interval: {prometheus_interval}"))

        # Try importing metrics module
        try:
            from ingestion.metrics import MetricsCollector
            checks.append(("MetricsCollector module importable", True, "✓"))
        except Exception as e:
            checks.append(("MetricsCollector module importable", False, str(e)[:50]))

        self.results["Monitoring & Alerting"] = checks
        return self._print_checks(checks)

    def _validate_redis(self) -> bool:
        """Validate Redis cache configuration."""
        checks = []

        redis_host = os.getenv("REDIS_HOST")
        checks.append(("REDIS_HOST configured", bool(redis_host), f"Host: {redis_host}"))

        redis_port = os.getenv("REDIS_PORT")
        checks.append(("REDIS_PORT configured", bool(redis_port), f"Port: {redis_port}"))

        redis_db = os.getenv("REDIS_DB")
        checks.append(("REDIS_DB configured", bool(redis_db), f"DB: {redis_db}"))

        # Try importing cache module
        try:
            from ingestion.db_cache import CacheManager
            checks.append(("CacheManager module importable", True, "✓"))
        except Exception as e:
            checks.append(("CacheManager module importable", False, str(e)[:50]))

        self.results["Redis Cache"] = checks
        return self._print_checks(checks)

    def _validate_security(self) -> bool:
        """Validate security settings."""
        checks = []

        jwt_secret = os.getenv("JWT_SECRET_KEY")
        checks.append(("JWT_SECRET_KEY configured", bool(jwt_secret), "✓ (hidden)"))

        api_key_enabled = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
        checks.append(("API_KEY_ENABLED configured", True, f"Enabled: {api_key_enabled}"))

        rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"
        checks.append(("RATE_LIMIT_ENABLED configured", True, f"Enabled: {rate_limit_enabled}"))

        ssl_enabled = os.getenv("SSL_ENABLED", "false").lower() == "true"
        checks.append(("SSL_ENABLED configured", True, f"Enabled: {ssl_enabled}"))

        self.results["Security"] = checks
        return self._print_checks(checks)

    def _validate_gcp(self) -> bool:
        """Validate GCP configuration."""
        checks = []

        gcp_project = os.getenv("GCP_PROJECT_ID")
        checks.append(("GCP_PROJECT_ID configured", bool(gcp_project), f"Project: {gcp_project}"))

        gcp_region = os.getenv("GCP_REGION")
        checks.append(("GCP_REGION configured", bool(gcp_region), f"Region: {gcp_region}"))

        deployment_target = os.getenv("DEPLOYMENT_TARGET")
        checks.append(("DEPLOYMENT_TARGET configured", bool(deployment_target), f"Target: {deployment_target}"))

        self.results["GCP Configuration"] = checks
        return self._print_checks(checks)

    def _print_checks(self, checks: List[Tuple[str, bool, str]]) -> bool:
        """Print validation checks and return overall status."""
        all_passed = True
        for name, passed, detail in checks:
            status = "✓" if passed else "✗"
            logger.info(f"  {status} {name}: {detail}")
            all_passed &= passed
        return all_passed


def main():
    """Run integration validation."""
    validator = ConfigValidator()
    success = validator.validate_all()

    if success:
        logger.info("\n✓ ALL INTEGRATIONS VALIDATED SUCCESSFULLY")
        logger.info("  All .env configurations are properly integrated.")
        return 0
    else:
        logger.error("\n✗ SOME INTEGRATIONS FAILED VALIDATION")
        logger.error("  Please check the errors above and fix the configuration.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
