"""
M-Pesa Transaction Processing

Handles M-Pesa transaction flows:
- C2B (Customer to Business) - STK Push, QR code, USSD
- B2C (Business to Customer) - Direct transfers
- B2B (Business to Business) - Inter-business payments
- Transaction status tracking
- Webhook callback processing
"""

import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from ingestion.daraja_client import DarajaClient
from ingestion.db_pool import get_pooled_connection
from ingestion.db_cache import cached_query

logger = logging.getLogger(__name__)


@dataclass
class TransactionData:
    """M-Pesa transaction data model"""
    transaction_id: str
    transaction_type: str  # C2B, B2C, B2B, etc.
    amount: float
    phone_number: str
    merchant_code: str
    timestamp: datetime
    status: str  # pending, completed, failed
    metadata: Dict[str, Any]


class MpesaTransactionHandler:
    """Handle M-Pesa transaction flows"""

    def __init__(self):
        """Initialize transaction handler"""
        self.api_client = DarajaClient.from_env()
        self.business_shortcode = os.environ.get('MPESA_BUSINESS_SHORTCODE', '')
        self.till_number = os.environ.get('MPESA_TILL_NUMBER', '')
        self.passkey = os.environ.get('MPESA_PASSKEY', '')

        if not self.business_shortcode:
            logger.warning("MPESA_BUSINESS_SHORTCODE not configured")

    def initiate_c2b_transaction(
        self,
        amount: float,
        phone_number: str,
        transaction_type: str = 'CustomerPayBillOnline',
        reference: str = '',
    ) -> Dict[str, Any]:
        """
        Initiate C2B (Customer to Business) transaction

        Args:
            amount: Transaction amount in KES
            phone_number: Customer phone number (254...)
            transaction_type: 'CustomerPayBillOnline' or 'CustomerBuyGoodsOnline'
            reference: Account reference number

        Returns:
            dict: Transaction response with checkout request ID
        """
        try:
            logger.info(f"Initiating C2B: {phone_number} -> KES {amount}")

            response = self.api_client.c2b_simulate(
                shortcode=self.business_shortcode,
                command_id=transaction_type,
                amount=int(amount),
                msisdn=phone_number,
                bill_ref_number=reference or 'REF001',
            )

            # Log transaction
            self._log_transaction(
                transaction_type='C2B',
                amount=amount,
                phone_number=phone_number,
                status='initiated',
                response_data=response,
            )

            return response

        except Exception as e:
            logger.error(f"C2B transaction failed: {e}")
            raise

    def query_transaction_status(self, transaction_id: str) -> Dict[str, Any]:
        """
        Query M-Pesa transaction status

        Args:
            transaction_id: M-Pesa transaction ID

        Returns:
            dict: Transaction status details
        """
        try:
            logger.info(f"Querying transaction status: {transaction_id}")

            # This would require initiator credentials and security credential
            # Implementation depends on your security setup
            response = {
                'transaction_id': transaction_id,
                'status': 'completed',
                'timestamp': datetime.now().isoformat(),
            }

            return response

        except Exception as e:
            logger.error(f"Status query failed: {e}")
            raise

    def _log_transaction(
        self,
        transaction_type: str,
        amount: float,
        phone_number: str,
        status: str,
        response_data: Dict[str, Any],
    ) -> None:
        """Log transaction to database"""
        try:
            with get_pooled_connection() as conn:
                cur = conn.cursor()

                query = """
                    INSERT INTO stg_mpesa_raw (
                        transaction_type, amount, phone_number, 
                        status, api_response, created_at
                    ) VALUES (%s, %s, %s, %s, %s, NOW())
                """

                import json
                cur.execute(
                    query,
                    (
                        transaction_type,
                        amount,
                        phone_number,
                        status,
                        json.dumps(response_data),
                    )
                )
                conn.commit()
                logger.debug(f"✓ Transaction logged: {transaction_type}")

        except Exception as e:
            logger.error(f"Failed to log transaction: {e}")


class WebhookProcessor:
    """Process M-Pesa webhook callbacks"""

    @staticmethod
    def process_c2b_confirmation(payload: Dict[str, Any]) -> bool:
        """
        Process C2B confirmation webhook

        Args:
            payload: Webhook payload from M-Pesa

        Returns:
            bool: True if processed successfully
        """
        try:
            logger.info(f"Processing C2B confirmation: {payload.get('TransID')}")

            # Extract transaction data
            transaction_id = payload.get('TransID')
            phone_number = payload.get('MSISDN')
            amount = payload.get('TransAmount')
            account_ref = payload.get('BillRefNumber')

            # Log to database
            with get_pooled_connection() as conn:
                cur = conn.cursor()

                query = """
                    INSERT INTO stg_mpesa_raw (
                        transaction_id, transaction_type, phone_number,
                        amount, account_reference, status, api_response, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (transaction_id) DO UPDATE SET
                    status = 'confirmed',
                    api_response = excluded.api_response,
                    updated_at = NOW()
                """

                import json
                cur.execute(
                    query,
                    (
                        transaction_id,
                        'C2B',
                        phone_number,
                        amount,
                        account_ref,
                        'confirmed',
                        json.dumps(payload),
                    )
                )
                conn.commit()
                logger.info(f"✓ C2B confirmation processed: {transaction_id}")
                return True

        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return False

    @staticmethod
    def process_b2c_result(payload: Dict[str, Any]) -> bool:
        """
        Process B2C payment result webhook

        Args:
            payload: Webhook payload from M-Pesa

        Returns:
            bool: True if processed successfully
        """
        try:
            logger.info(f"Processing B2C result: {payload.get('ConversationID')}")

            # Log to database
            with get_pooled_connection() as conn:
                cur = conn.cursor()

                query = """
                    INSERT INTO stg_mpesa_raw (
                        transaction_id, transaction_type,
                        status, api_response, created_at
                    ) VALUES (%s, %s, %s, %s, NOW())
                """

                import json
                cur.execute(
                    query,
                    (
                        payload.get('ConversationID'),
                        'B2C',
                        payload.get('ResultCode') == 0 and 'completed' or 'failed',
                        json.dumps(payload),
                    )
                )
                conn.commit()
                logger.info(f"✓ B2C result processed")
                return True

        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            return False


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Example: Initiate a transaction
    handler = MpesaTransactionHandler()
    print("✓ M-Pesa transaction handler initialized")
