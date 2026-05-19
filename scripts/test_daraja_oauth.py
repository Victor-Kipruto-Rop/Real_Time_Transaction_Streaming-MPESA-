#!/usr/bin/env python
"""
Test Daraja OAuth connection
"""

import os
import sys
import logging

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
    logger.info("Testing Daraja OAuth Connection")
    logger.info("=" * 70)
    logger.info("")
    
    client = DarajaClient.from_env()
    token = client.get_access_token()
    
    logger.info(f"✓ Daraja OAuth connection successful")
    logger.info(f"  Token (first 50 chars): {token[:50]}...")
    logger.info(f"  Token length: {len(token)} characters")
    logger.info("")
    logger.info("✓ Daraja credentials are valid and working")
    sys.exit(0)

except Exception as e:
    logger.error(f"✗ Daraja OAuth connection failed: {e}")
    logger.exception(e)
    sys.exit(1)
