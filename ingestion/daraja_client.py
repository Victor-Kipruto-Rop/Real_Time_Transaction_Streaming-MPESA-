"""
Safaricom Daraja API client.

Handles OAuth2 authentication and API interactions with Safaricom's
M-Pesa Daraja platform for C2B and STK Push operations.
"""

from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from schemas.transaction_schema import normalize_ke_phone

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DarajaConfig:
    environment: str
    consumer_key: str
    consumer_secret: str
    business_shortcode: str
    passkey: Optional[str] = None
    callback_url: Optional[str] = None


class DarajaClient:
    """
    Client for Safaricom Daraja API interactions.

    Attributes:
        consumer_key (str): API consumer key
        consumer_secret (str): API consumer secret
        business_shortcode (str): M-Pesa business shortcode
        access_token (str): Current OAuth2 access token
        token_expiry (datetime): Token expiration time
    """

    def __init__(
        self,
        consumer_key: str,
        consumer_secret: str,
        business_shortcode: str,
        passkey: Optional[str] = None,
        callback_url: Optional[str] = None,
        environment: str = "sandbox",
    ):
        """
        Initialize Daraja API client.

        Args:
            consumer_key: Safaricom API consumer key
            consumer_secret: Safaricom API consumer secret
            business_shortcode: M-Pesa business shortcode
            environment: 'sandbox' or 'production'
        """
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.business_shortcode = business_shortcode
        self.passkey = passkey
        self.callback_url = callback_url
        self.environment = environment

        # Base URLs
        if environment == "sandbox":
            self.base_url = "https://sandbox.safaricom.co.ke"
        else:
            self.base_url = "https://api.safaricom.co.ke"

        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._session = requests.Session()

    @classmethod
    def from_env(cls) -> "DarajaClient":
        environment = os.getenv("DARAJA_ENVIRONMENT", "sandbox").strip() or "sandbox"
        consumer_key = os.getenv("DARAJA_CONSUMER_KEY") or os.getenv("DARAJA_KEY")
        consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET") or os.getenv(
            "DARAJA_SECRET"
        )
        business_shortcode = (
            os.getenv("MPESA_BUSINESS_SHORTCODE")
            or os.getenv("DARAJA_BUSINESS_SHORTCODE")
            or os.getenv("DARAJA_SHORTCODE")
            or os.getenv("DARAJA_C2B_SHORTCODE")
            or os.getenv("BUSINESS_SHORTCODE")
        )
        passkey = os.getenv("MPESA_PASSKEY") or os.getenv("DARAJA_PASSKEY")
        callback_url = os.getenv("CALLBACK_URL") or os.getenv("DARAJA_CALLBACK_URL")

        missing = [
            name
            for name, val in [
                ("DARAJA_CONSUMER_KEY", consumer_key),
                ("DARAJA_CONSUMER_SECRET", consumer_secret),
                ("MPESA_BUSINESS_SHORTCODE", business_shortcode),
            ]
            if not val
        ]
        if missing:
            raise ValueError(f"Missing required Daraja env vars: {', '.join(missing)}")

        assert consumer_key is not None
        assert consumer_secret is not None
        assert business_shortcode is not None

        return cls(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            business_shortcode=business_shortcode,
            passkey=passkey,
            callback_url=callback_url,
            environment=environment,
        )

    def get_access_token(self) -> str:
        """
        Obtain OAuth2 access token from Daraja API.

        Returns:
            str: Access token

        Raises:
            Exception: If token retrieval fails
        """
        # Check if token is still valid
        if (
            self.access_token
            and self.token_expiry
            and datetime.now() < self.token_expiry
        ):
            return self.access_token

        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

        try:
            response = self._session.get(
                url, auth=(self.consumer_key, self.consumer_secret), timeout=10
            )
            response.raise_for_status()

            data = response.json()
            access_token = data.get("access_token")
            if not isinstance(access_token, str) or not access_token:
                raise ValueError("Daraja OAuth response did not include access_token")
            self.access_token = access_token
            expires_in = int(data.get("expires_in") or 3600)
            # Refresh a bit early.
            self.token_expiry = datetime.now() + timedelta(
                seconds=max(expires_in - 300, 60)
            )

            logger.info("Access token obtained successfully")
            return self.access_token

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get access token: {str(e)}")
            raise

    def _stk_password(self, timestamp: str) -> str:
        if not self.passkey:
            raise ValueError(
                "MPESA_PASSKEY is required for STK push password generation"
            )
        raw = f"{self.business_shortcode}{self.passkey}{timestamp}".encode("utf-8")
        return base64.b64encode(raw).decode("utf-8")

    def c2b_register_url(
        self,
        validation_url: Optional[str] = None,
        confirmation_url: Optional[str] = None,
        response_type: str = "Canceled",
        shortcode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Register C2B validation and confirmation URLs.

        Args:
            validation_url: URL for transaction validation
            confirmation_url: URL for transaction confirmation
            response_type: 'Canceled' or 'Completed'

        Returns:
            dict: API response
        """
        token = self.get_access_token()

        validation_url = validation_url or os.getenv("C2B_VALIDATION_URL")
        confirmation_url = confirmation_url or os.getenv("C2B_CONFIRMATION_URL")
        if not validation_url or not confirmation_url:
            raise ValueError(
                "validation_url and confirmation_url are required (or set env vars)"
            )

        url = f"{self.base_url}/mpesa/c2b/v1/registerurl"

        payload = {
            "ShortCode": shortcode or self.business_shortcode,
            "ResponseType": response_type,
            "ConfirmationURL": confirmation_url,
            "ValidationURL": validation_url,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = self._session.post(
                url, json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            logger.info("C2B URLs registered successfully")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"C2B registration failed: {str(e)}")
            raise

    def register_url(
        self,
        shortcode: Optional[str] = None,
        response_type: str = "Completed",
        confirmation_url: Optional[str] = None,
        validation_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Compatibility wrapper for older Daraja helper scripts."""
        return self.c2b_register_url(
            validation_url=validation_url,
            confirmation_url=confirmation_url,
            response_type=response_type,
            shortcode=shortcode,
        )

    def c2b_simulate(
        self,
        shortcode: Optional[str] = None,
        command_id: str = "CustomerPayBillOnline",
        amount: int = 1,
        msisdn: str = "254708374149",
        bill_ref_number: str = "TEST001",
    ) -> Dict[str, Any]:
        """Simulate a sandbox C2B customer payment."""
        if amount <= 0:
            raise ValueError("amount must be > 0")

        token = self.get_access_token()
        url = f"{self.base_url}/mpesa/c2b/v1/simulate"
        payload = {
            "ShortCode": shortcode or self.business_shortcode,
            "CommandID": command_id,
            "Amount": amount,
            "Msisdn": normalize_ke_phone(msisdn),
            "BillRefNumber": bill_ref_number,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = self._session.post(
                url, json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            logger.info("C2B simulation submitted successfully")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"C2B simulation failed: {str(e)}")
            raise

    def initiate_stk_push(
        self,
        phone_number: str,
        amount: int,
        account_reference: str = "REF123",
        callback_url: Optional[str] = None,
        description: str = "Payment",
    ) -> Dict[str, Any]:
        """
        Initiate STK push (prompt) for customer payment.

        Args:
            phone_number: Customer phone number (254XXXXXXXXX format)
            amount: Amount in KES
            description: Transaction description

        Returns:
            dict: API response with checkout_request_id
        """
        token = self.get_access_token()

        url = f"{self.base_url}/mpesa/stkpush/v1/processrequest"

        if amount <= 0:
            raise ValueError("amount must be > 0")

        phone_number = normalize_ke_phone(phone_number)

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self._stk_password(timestamp)

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone_number,
            "PartyB": self.business_shortcode,
            "PhoneNumber": phone_number,
            "CallBackURL": callback_url
            or self.callback_url
            or os.getenv("CALLBACK_URL", "https://example.com/callback"),
            "AccountReference": account_reference,
            "TransactionDesc": description,
        }

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = self._session.post(
                url, json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()
            logger.info(f"STK push initiated for {phone_number}")
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"STK push failed: {str(e)}")
            raise


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    client = DarajaClient.from_env()

    # Get access token
    token = client.get_access_token()
    print(f"Token obtained: {token[:20]}...")
