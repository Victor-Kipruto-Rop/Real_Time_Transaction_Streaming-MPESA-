"""
M-Pesa Transaction Streaming Ingestion Module

This module handles real-time ingestion of M-Pesa transactions through:
- Safaricom Daraja API (C2B, B2C, STK Push callbacks)
- Webhook receivers for transaction notifications
- Kafka producer for event streaming
"""

__version__ = "1.0.0"
__author__ = "Data Engineering Team"
