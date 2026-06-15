from data_quality.validation import TransactionValidator
import logging


def test_validator():
    valid_tx = {
        "TransactionID": "TXN123456",
        "Amount": 1500.50,
        "PhoneNumber": "254712345678",
        "ShortCode": "174379",
        "TransactionTime": "2026-06-15T08:00:00",
    }

    invalid_phone = valid_tx.copy()
    invalid_phone["PhoneNumber"] = "0712345678"

    invalid_amount = valid_tx.copy()
    invalid_amount["Amount"] = -100

    print("Testing Valid Transaction:")
    assert TransactionValidator.validate(valid_tx) is True

    print("\nTesting Invalid Phone:")
    assert TransactionValidator.validate(invalid_phone) is False

    print("\nTesting Invalid Amount:")
    assert TransactionValidator.validate(invalid_amount) is False

    print("\nAll tests passed successfully.")


if __name__ == "__main__":
    test_validator()
