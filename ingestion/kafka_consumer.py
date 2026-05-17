"""
Kafka Consumer for M-Pesa Transaction Streaming
Consumes messages from Kafka topic and processes Safaricom C2B transactions
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import sys

from kafka import KafkaConsumer
from kafka.errors import KafkaError
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/kafka_consumer.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class SafaricomTransactionProcessor:
    """Process and store Safaricom M-Pesa transactions"""

    def __init__(self):
        """Initialize processor with database and Kafka connections"""
        self.db_connection = None
        self.consumer = None
        self.processed_count = 0
        self.error_count = 0

        # Database configuration
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", 5433)),
            "database": os.getenv("DB_NAME", "mpesa_analytics"),
            "user": os.getenv("DB_USER", "data_engineer"),
            "password": os.getenv("DB_PASSWORD", "change_me"),
        }

        # Kafka configuration
        self.kafka_config = {
            "bootstrap_servers": os.getenv("KAFKA_BROKERS", "localhost:9092").split(
                ","
            ),
            "group_id": os.getenv("KAFKA_GROUP_ID", "mpesa-consumer-group"),
            "topic": os.getenv("KAFKA_TOPIC", "mpesa-transactions"),
            "auto_offset_reset": "earliest",
            "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
        }

        self._connect_db()
        self._connect_kafka()

    def _connect_db(self):
        """Establish database connection"""
        try:
            self.db_connection = psycopg2.connect(**self.db_config)
            logger.info(f"Connected to database: {self.db_config['database']}")
        except psycopg2.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _connect_kafka(self):
        """Establish Kafka consumer connection"""
        try:
            self.consumer = KafkaConsumer(
                self.kafka_config["topic"],
                bootstrap_servers=self.kafka_config["bootstrap_servers"],
                group_id=self.kafka_config["group_id"],
                auto_offset_reset=self.kafka_config["auto_offset_reset"],
                value_deserializer=self.kafka_config["value_deserializer"],
                enable_auto_commit=True,
                max_poll_records=100,
            )
            logger.info(f"Connected to Kafka topic: {self.kafka_config['topic']}")
        except KafkaError as e:
            logger.error(f"Kafka connection failed: {e}")
            raise

    def parse_c2b_transaction(
        self, message: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Parse C2B transaction from Safaricom webhook"""
        try:
            return {
                "transaction_id": message.get("TransID", ""),
                "phone_number": message.get("MSISDN", ""),
                "business_shortcode": message.get("BusinessShortCode", ""),
                "amount": float(message.get("TransAmount", 0)),
                "transaction_time": message.get("TransTime", ""),
                "transaction_status": "completed",
                "payment_method": "c2b",
                "reference": message.get("BillRefNumber", ""),
                "account_reference": message.get("AccountReference", ""),
                "merchant_id": message.get("BusinessShortCode", ""),
                "region": self._extract_region(message.get("MSISDN", "")),
                "processed_at": datetime.utcnow().isoformat(),
                "raw_data": json.dumps(message),
            }
        except Exception as e:
            logger.error(f"Transaction parsing error: {e}")
            return None

    def _extract_region(self, phone: str) -> Optional[str]:
        """Extract region from phone number"""
        # Kenya phone number regions mapping
        regions = {
            "0700": "Nairobi",
            "0701": "Nairobi",
            "0702": "Nairobi",
            "0703": "Nairobi",
            "0704": "Central",
            "0705": "Coast",
            "0706": "Coast",
            "0707": "Rift Valley",
            "0708": "Western",
            "0709": "Western",
            "0710": "Central",
            "0711": "Eastern",
            "0712": "Nyanza",
            "0713": "Nairobi",
            "0714": "Nairobi",
            "0715": "Western",
            "0716": "Coast",
            "0717": "Nairobi",
            "0718": "Central",
            "0719": "Nairobi",
            "0720": "Nairobi",
            "0721": "Nairobi",
            "0722": "Nairobi",
            "0723": "Nairobi",
            "0724": "Central",
            "0725": "Eastern",
            "0726": "Western",
            "0727": "Rift Valley",
            "0728": "Nyanza",
            "0729": "Coast",
            "0740": "Nairobi",
            "0741": "Central",
            "0742": "Rift Valley",
            "0743": "Western",
            "0744": "Nyanza",
            "0745": "Coast",
            "0746": "Eastern",
            "0748": "Nairobi",
            "0749": "Central",
            "0750": "Nairobi",
            "0751": "Rift Valley",
            "0752": "Western",
            "0753": "Nyanza",
            "0754": "Coast",
            "0755": "Eastern",
            "0756": "Nairobi",
            "0757": "Central",
            "0758": "Nairobi",
            "0759": "Rift Valley",
            "0760": "Western",
            "0761": "Nyanza",
            "0762": "Coast",
            "0763": "Eastern",
            "0764": "Nairobi",
            "0765": "Central",
            "0768": "Nairobi",
            "0769": "Nairobi",
            "0771": "Nairobi",
            "0772": "Nairobi",
            "0773": "Nairobi",
            "0774": "Nairobi",
            "0775": "Nairobi",
            "0776": "Nairobi",
            "0777": "Nairobi",
            "0778": "Nairobi",
            "0779": "Nairobi",
            "0780": "Nairobi",
            "0781": "Nairobi",
            "0782": "Nairobi",
            "0783": "Nairobi",
        }

        prefix = phone[:4] if len(phone) >= 4 else phone
        return regions.get(prefix, "Unknown")

    def insert_transaction(self, transaction: Dict[str, Any]) -> bool:
        """Insert transaction into database"""
        if not transaction:
            return False

        try:
            cursor = self.db_connection.cursor()

            # Insert into raw transactions table
            insert_query = """
            INSERT INTO mpesa_transactions_raw
            (transaction_id, phone_number, amount, business_shortcode,
             transaction_time, transaction_status, payment_method,
             reference, account_reference, merchant_id, region, processed_at, raw_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (transaction_id) DO NOTHING
            """

            cursor.execute(
                insert_query,
                (
                    transaction["transaction_id"],
                    transaction["phone_number"],
                    transaction["amount"],
                    transaction["business_shortcode"],
                    transaction["transaction_time"],
                    transaction["transaction_status"],
                    transaction["payment_method"],
                    transaction["reference"],
                    transaction["account_reference"],
                    transaction["merchant_id"],
                    transaction["region"],
                    transaction["processed_at"],
                    transaction["raw_data"],
                ),
            )

            self.db_connection.commit()
            self.processed_count += 1

            if self.processed_count % 100 == 0:
                logger.info(f"Processed {self.processed_count} transactions")

            return True

        except psycopg2.Error as e:
            logger.error(f"Database insert error: {e}")
            self.db_connection.rollback()
            self.error_count += 1
            return False
        finally:
            cursor.close()

    def batch_insert_transactions(self, transactions: list) -> bool:
        """Batch insert multiple transactions"""
        if not transactions:
            return False

        try:
            cursor = self.db_connection.cursor()

            # Prepare batch data
            batch_data = [
                (
                    t["transaction_id"],
                    t["phone_number"],
                    t["amount"],
                    t["business_shortcode"],
                    t["transaction_time"],
                    t["transaction_status"],
                    t["payment_method"],
                    t["reference"],
                    t["account_reference"],
                    t["merchant_id"],
                    t["region"],
                    t["processed_at"],
                    t["raw_data"],
                )
                for t in transactions
                if t
            ]

            insert_query = """
            INSERT INTO mpesa_transactions_raw
            (transaction_id, phone_number, amount, business_shortcode,
             transaction_time, transaction_status, payment_method,
             reference, account_reference, merchant_id, region, processed_at, raw_data)
            VALUES %s
            ON CONFLICT (transaction_id) DO NOTHING
            """

            if batch_data:
                execute_values(cursor, insert_query, batch_data)
                self.db_connection.commit()
                self.processed_count += len(batch_data)
                logger.info(f"Batch inserted {len(batch_data)} transactions")

            return True

        except psycopg2.Error as e:
            logger.error(f"Batch insert error: {e}")
            self.db_connection.rollback()
            self.error_count += len(transactions)
            return False
        finally:
            cursor.close()

    def process_stream(self):
        """Main stream processing loop"""
        logger.info("Starting Kafka consumer stream...")

        batch = []
        batch_size = 100

        try:
            for message in self.consumer:
                try:
                    # Parse transaction
                    transaction = self.parse_c2b_transaction(message.value)

                    if transaction:
                        batch.append(transaction)

                    # Insert when batch is full
                    if len(batch) >= batch_size:
                        self.batch_insert_transactions(batch)
                        batch = []

                except Exception as e:
                    logger.error(f"Message processing error: {e}")
                    self.error_count += 1
                    continue

        except KeyboardInterrupt:
            logger.info("Consumer interrupted by user")

        finally:
            # Insert remaining batch
            if batch:
                self.batch_insert_transactions(batch)

            # Print statistics
            logger.info("Stream processing stopped")
            logger.info(f"Total processed: {self.processed_count}")
            logger.info(f"Total errors: {self.error_count}")

            self.close()

    def close(self):
        """Close connections"""
        if self.consumer:
            self.consumer.close()
        if self.db_connection:
            self.db_connection.close()
        logger.info("Connections closed")

    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "error_rate": (
                self.error_count / (self.processed_count + self.error_count) * 100
            )
            if (self.processed_count + self.error_count) > 0
            else 0,
        }


def main():
    """Main entry point"""
    try:
        processor = SafaricomTransactionProcessor()
        processor.process_stream()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
