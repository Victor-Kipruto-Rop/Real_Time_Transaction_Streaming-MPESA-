#!/usr/bin/env python
"""
Test C2B transaction simulation with Daraja sandbox
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
    logger.info("Testing C2B Transaction Simulation (Daraja Sandbox)")
    logger.info("=" * 70)

    client = DarajaClient.from_env()

    # Get test parameters from environment
    shortcode = (
        os.environ.get("DARAJA_C2B_SHORTCODE")
        or os.environ.get("DARAJA_SHORTCODE")
        or os.environ.get("MPESA_BUSINESS_SHORTCODE")
    )
    amount = int(os.environ.get('DARAJA_TEST_AMOUNT', '10'))
    msisdn = os.environ.get('DARAJA_TEST_MSISDN', '254708374149')
    bill_ref = os.environ.get('DARAJA_TEST_BILL_REF', 'TEST001')

    logger.info("Parameters:")
    logger.info(f"  Shortcode: {shortcode}")
    logger.info(f"  Amount: KES {amount}")
    logger.info(f"  Phone: {msisdn}")
    logger.info(f"  Reference: {bill_ref}")
    logger.info("")

    # Initiate C2B transaction
    result = client.c2b_simulate(
        shortcode=shortcode,
        command_id='CustomerPayBillOnline',
        amount=amount,
        msisdn=msisdn,
        bill_ref_number=bill_ref,
    )

    logger.info("Response:")
    for key, value in result.items():
        logger.info(f"  {key}: {value}")

    if result.get('ResponseCode') == '0' or 'CheckoutRequestID' in result:
        logger.info("")
        logger.info("✓ C2B test SUCCESSFUL")
        logger.info(f"  Checkout Request ID: {result.get('CheckoutRequestID')}")
        sys.exit(0)
    else:
        logger.error("")
        logger.error("✗ C2B test FAILED")
        logger.error(f"  Response Code: {result.get('ResponseCode')}")
        sys.exit(1)

except Exception as e:
    logger.error(f"✗ C2B test FAILED with exception: {e}")
    logger.exception(e)
    sys.exit(1)
