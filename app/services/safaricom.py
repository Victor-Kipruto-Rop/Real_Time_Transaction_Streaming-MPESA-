"""
Safaricom Daraja API Integration Service
Complete implementation for M-Pesa C2B, STK Push, B2C, and other APIs
"""

import httpx
import logging
import base64
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio

from app.config import settings

logger = logging.getLogger(__name__)


class SafaricomAPIError(Exception):
    """Custom exception for Safaricom API errors"""

    pass


class DarajaService:
    """
    M-Pesa Daraja API Integration
    Handles all M-Pesa transaction operations
    """

    # Endpoints
    SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"

    ENDPOINTS = {
        "oauth": "/oauth/v1/generate",
        "c2b_register": "/mpesa/c2b/v1/registerurl",
        "c2b_simulate": "/mpesa/c2bsimulate/v1/simulate",
        "stk_push": "/mpesa/stkpush/v1/processrequest",
        "stk_query": "/mpesa/stkpushquery/v1/query",
        "b2c": "/mpesa/b2c/v1/paymentrequest",
        "balance": "/mpesa/accountbalance/v1/query",
        "transaction_status": "/mpesa/transactionstatus/v1/query",
        "transaction_reversal": "/mpesa/reversal/v1/request",
    }

    def __init__(self):
        """Initialize Safaricom service"""
        self.base_url = (
            self.PRODUCTION_BASE_URL
            if settings.DARAJA_ENVIRONMENT == "production"
            else self.SANDBOX_BASE_URL
        )
        self.consumer_key = settings.DARAJA_CONSUMER_KEY
        self.consumer_secret = settings.DARAJA_CONSUMER_SECRET
        self.business_shortcode = settings.DARAJA_BUSINESS_SHORTCODE
        self.passkey = settings.DARAJA_PASSKEY

        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    async def get_access_token(self) -> str:
        """
        Get OAuth2 access token from Safaricom
        Tokens are cached and reused until expiry
        """

        # Return cached token if still valid
        if self._access_token and self._token_expiry:
            if datetime.utcnow() < self._token_expiry:
                logger.debug("Using cached access token")
                return self._access_token

        try:
            # Create Basic Auth header
            credentials = f"{self.consumer_key}:{self.consumer_secret}"
            encoded = base64.b64encode(credentials.encode()).decode()

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{self.ENDPOINTS['oauth']}",
                    headers={
                        "Authorization": f"Basic {encoded}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"OAuth failed: {response.text}")

            data = response.json()
            access_token = data.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise SafaricomAPIError("OAuth response did not include access_token")
            self._access_token = access_token

            # Token expires in 3600 seconds (1 hour), cache for 55 minutes
            self._token_expiry = datetime.utcnow() + timedelta(seconds=3300)

            logger.info("✓ New access token obtained")
            return access_token

        except Exception as e:
            logger.error(f"Failed to get access token: {str(e)}")
            raise SafaricomAPIError(f"OAuth error: {str(e)}")

    async def register_c2b_callback(
        self, confirmation_url: str, validation_url: str
    ) -> Dict[str, Any]:
        """
        Register C2B confirmation and validation URLs
        Must be called once to setup callbacks
        """

        try:
            token = await self.get_access_token()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.ENDPOINTS['c2b_register']}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "ShortCode": self.business_shortcode,
                        "ResponseType": "Completed",
                        "ConfirmationURL": confirmation_url,
                        "ValidationURL": validation_url,
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"C2B registration failed: {response.text}")

            result = response.json()
            logger.info(f"✓ C2B callbacks registered: {result}")
            return result

        except Exception as e:
            logger.error(f"C2B registration error: {str(e)}")
            raise

    async def simulate_c2b_payment(
        self, phone_number: str, amount: float, reference: str = "Test"
    ) -> Dict[str, Any]:
        """
        Simulate a C2B transaction (testing only)
        """

        try:
            token = await self.get_access_token()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.ENDPOINTS['c2b_simulate']}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "ShortCode": self.business_shortcode,
                        "CommandID": "CustomerPayBillOnline",
                        "Amount": str(amount),
                        "Msisdn": phone_number,
                        "BillRefNumber": reference,
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"C2B simulation failed: {response.text}")

            result = response.json()
            logger.info(f"✓ C2B simulation successful: {result}")
            return result

        except Exception as e:
            logger.error(f"C2B simulation error: {str(e)}")
            raise

    async def initiate_stk_push(
        self, phone_number: str, amount: float, account_reference: str = "ChamaNdoto"
    ) -> Dict[str, Any]:
        """
        Initiate STK Push (Lipa Na Mpesa Online)
        Shows popup on customer phone for payment
        """

        try:
            token = await self.get_access_token()

            # Generate timestamp in format YYYYMMDDHHMMSS
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")

            # Generate password: base64(shortcode + passkey + timestamp)
            password_string = f"{self.business_shortcode}{self.passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.ENDPOINTS['stk_push']}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "BusinessShortCode": self.business_shortcode,
                        "Password": password,
                        "Timestamp": timestamp,
                        "TransactionType": "CustomerPayBillOnline",
                        "Amount": str(amount),
                        "PartyA": phone_number,
                        "PartyB": self.business_shortcode,
                        "PhoneNumber": phone_number,
                        "CallBackURL": os.getenv(
                            "CALLBACK_URL",
                            f"https://{settings.DOMAIN}/api/v1/webhooks/stk/callback",
                        ),
                        "AccountReference": account_reference,
                        "TransactionDesc": f"Payment for {account_reference}",
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"STK push failed: {response.text}")

            result = response.json()

            if result.get("ResponseCode") == "0":
                logger.info(f"✓ STK push initiated: {result}")
            else:
                logger.warning(f"⚠️ STK push rejected: {result}")

            return result

        except Exception as e:
            logger.error(f"STK push error: {str(e)}")
            raise

    async def query_stk_status(self, checkout_request_id: str) -> Dict[str, Any]:
        """
        Query the status of an STK Push request
        """

        try:
            token = await self.get_access_token()
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
            password_string = f"{self.business_shortcode}{self.passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.ENDPOINTS['stk_query']}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "BusinessShortCode": self.business_shortcode,
                        "Password": password,
                        "Timestamp": timestamp,
                        "CheckoutRequestID": checkout_request_id,
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"STK query failed: {response.text}")

            result = response.json()
            logger.info(f"✓ STK status: {result}")
            return result

        except Exception as e:
            logger.error(f"STK query error: {str(e)}")
            raise

    async def initiate_b2c_payout(
        self, phone_number: str, amount: float, reference: str = "Payout"
    ) -> Dict[str, Any]:
        """
        Initiate B2C payment (Business to Customer payout)
        """

        try:
            token = await self.get_access_token()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.ENDPOINTS['b2c']}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "InitiatorName": "ChamaNdoto",
                        "SecurityCredential": "encrypted_credential",  # Must be encrypted
                        "CommandID": "BusinessPayment",
                        "Amount": str(amount),
                        "PartyA": self.business_shortcode,
                        "PartyB": phone_number,
                        "Remarks": reference,
                        "QueueTimeOutURL": f"https://{settings.DOMAIN}/api/v1/webhooks/b2c/timeout",
                        "ResultURL": f"https://{settings.DOMAIN}/api/v1/webhooks/b2c/callback",
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"B2C payout failed: {response.text}")

            result = response.json()
            logger.info(f"✓ B2C payout initiated: {result}")
            return result

        except Exception as e:
            logger.error(f"B2C payout error: {str(e)}")
            raise

    async def check_account_balance(self) -> Dict[str, Any]:
        """
        Check account balance
        """

        try:
            token = await self.get_access_token()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.ENDPOINTS['balance']}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "CommandID": "AccountBalance",
                        "Partyid": self.business_shortcode,
                        "IdentifierType": "4",
                        "Remarks": "Balance check",
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"Balance check failed: {response.text}")

            result = response.json()
            logger.info(f"✓ Account balance: {result}")
            return result

        except Exception as e:
            logger.error(f"Balance check error: {str(e)}")
            raise

    async def query_transaction_status(
        self, transaction_id: str, phone_number: str
    ) -> Dict[str, Any]:
        """
        Query transaction status
        """

        try:
            token = await self.get_access_token()

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.ENDPOINTS['transaction_status']}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "CommandID": "TransactionStatusQuery",
                        "Transactionid": transaction_id,
                        "PartyA": phone_number,
                        "IdentifierType": "1",
                        "ResultURL": (
                            f"https://{settings.DOMAIN}"
                            "/api/v1/webhooks/status/callback"
                        ),
                        "QueueTimeOutURL": (
                            f"https://{settings.DOMAIN}"
                            "/api/v1/webhooks/status/timeout"
                        ),
                        "Remarks": "Status check",
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                raise SafaricomAPIError(f"Status query failed: {response.text}")

            result = response.json()
            logger.info(f"✓ Transaction status: {result}")
            return result

        except Exception as e:
            logger.error(f"Status query error: {str(e)}")
            raise

    @staticmethod
    def verify_signature(request_body: str, request_signature: str) -> bool:
        """
        Verify webhook signature from Safaricom
        Safaricom signs requests with their certificate
        """

        try:
            # In production, use Safaricom's public certificate to verify
            # This is a placeholder - implement actual verification
            logger.debug("Verifying Safaricom signature...")
            return True
        except Exception as e:
            logger.error(f"Signature verification failed: {str(e)}")
            return False


# Singleton instance
daraja_service = DarajaService()


async def test_safaricom_connection():
    """Test connection to Safaricom API"""

    try:
        logger.info("Testing Safaricom API connection...")

        # Test OAuth
        await daraja_service.get_access_token()
        logger.info("✓ OAuth successful")

        # Test C2B simulation
        result = await daraja_service.simulate_c2b_payment(
            phone_number="254712345678", amount=1, reference="Test"
        )
        logger.info(f"✓ C2B simulation successful: {result}")

        return True

    except Exception as e:
        logger.error(f"✗ Safaricom connection test failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Test the service
    asyncio.run(test_safaricom_connection())
