"""
Data Quality Validation Module
Robust validation for real-time M-Pesa transaction data.
"""

import logging
import re
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TransactionValidator:
    REQUIRED_FIELDS = ["TransactionID", "Amount", "PhoneNumber", "ShortCode", "TransactionTime"]
    PHONE_REGEX = re.compile(r"^254\d{9}$")

    @classmethod
    def validate(cls, transaction: Dict[str, Any]) -> bool:
        """Performs all necessary validations on a transaction record."""
        return (
            cls._check_schema(transaction) and
            cls._check_types(transaction) and
            cls._check_business_rules(transaction)
        )

    @classmethod
    def _check_schema(cls, transaction: Dict[str, Any]) -> bool:
        for field in cls.REQUIRED_FIELDS:
            if field not in transaction:
                logger.error(f"Schema Validation Failed: Missing field '{field}'")
                return False
        return True

    @classmethod
    def _check_types(cls, transaction: Dict[str, Any]) -> bool:
        try:
            float(transaction["Amount"])
            if not cls.PHONE_REGEX.match(str(transaction["PhoneNumber"])):
                logger.error(f"Type/Format Validation Failed: Invalid phone number format: {transaction['PhoneNumber']}")
                return False
            # Basic ISO timestamp check
            datetime.fromisoformat(transaction["TransactionTime"])
        except (ValueError, TypeError, KeyError) as e:
            logger.error(f"Type/Format Validation Failed: {e}")
            return False
        return True

    @classmethod
    def _check_business_rules(cls, transaction: Dict[str, Any]) -> bool:
        amount = float(transaction["Amount"])
        if amount <= 0:
            logger.error(f"Business Rule Validation Failed: Non-positive amount: {amount}")
            return False
        return True

