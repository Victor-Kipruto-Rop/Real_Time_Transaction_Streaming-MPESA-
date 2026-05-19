#!/usr/bin/env python
"""
Register C2B validation and confirmation URLs with Daraja
"""

import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from ingestion.daraja_client import DarajaClient

    logger.info("=" * 70)
    logger.info("Registering C2B URLs (Daraja Sandbox)")
    logger.info("=" * 70)

    client = DarajaClient.from_env()

    # Get configuration from environment
    shortcode = (
        os.environ.get("DARAJA_C2B_SHORTCODE")
        or os.environ.get("DARAJA_SHORTCODE")
        or os.environ.get("MPESA_BUSINESS_SHORTCODE")
    )
    response_type = os.environ.get("DARAJA_RESPONSE_TYPE", "Completed")
    validation_url = os.environ.get("DARAJA_VALIDATION_URL") or os.environ.get(
        "C2B_VALIDATION_URL"
    )
    confirmation_url = os.environ.get("DARAJA_CONFIRMATION_URL") or os.environ.get(
        "C2B_CONFIRMATION_URL"
    )

    if not validation_url:
        logger.error("✗ DARAJA_VALIDATION_URL not set in environment")
        sys.exit(1)

    if not confirmation_url:
        logger.error("✗ DARAJA_CONFIRMATION_URL not set in environment")
        sys.exit(1)

    logger.info("Parameters:")
    logger.info(f"  Shortcode: {shortcode}")
    logger.info(f"  Response Type: {response_type}")
    logger.info(f"  Validation URL: {validation_url}")
    logger.info(f"  Confirmation URL: {confirmation_url}")
    logger.info("")

    # Register URLs
    result = client.register_url(
        shortcode=shortcode,
        response_type=response_type,
        confirmation_url=confirmation_url,
        validation_url=validation_url,
    )

    logger.info("Response:")
    for key, value in result.items():
        logger.info(f"  {key}: {value}")

    if result.get('ResponseCode') == '0':
        logger.info("")
        logger.info("✓ URLs registered SUCCESSFULLY")
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. M-Pesa will now send validation and confirmation callbacks")
        logger.info(f"  2. Validation URL: {validation_url}")
        logger.info(f"  3. Confirmation URL: {confirmation_url}")
        logger.info("  4. Make sure your webhook endpoints are running")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("✗ URL registration FAILED")
        logger.error(f"  Response Code: {result.get('ResponseCode')}")
        logger.error(f"  Description: {result.get('ResponseDescription')}")
        sys.exit(1)

except Exception as e:
    logger.error(f"✗ URL registration FAILED with exception: {e}")
    logger.exception(e)
    sys.exit(1)
