# M-Pesa Real-Time Transaction Streaming - API Integration Guide

## Daraja API Reference

### Authentication

All Daraja API endpoints require OAuth2 Bearer token authentication.

#### Token Endpoint

```
POST /oauth/v1/generate?grant_type=client_credentials
Host: api.sandbox.safaricom.co.ke (sandbox)
Host: api.safaricom.co.ke (production)
```

**Request Headers:**
```
Authorization: Basic base64(consumer_key:consumer_secret)
Content-Type: application/x-www-form-urlencoded
```

**Response:**
```json
{
  "access_token": "smbV1HefJch...",
  "expires_in": 3599,
  "token_type": "Bearer"
}
```

**Token Caching:**
- Tokens are cached in-memory and reused until expiry
- Automatic refresh happens 30 seconds before expiry
- Tokens are never stored on disk (security)

---

### C2B (Customer-to-Business) APIs

#### 1. Register Confirmation & Validation URLs

```
POST /mpesa/c2b/v1/registerurl
Host: api.sandbox.safaricom.co.ke (sandbox)
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "ShortCode": "174379",
  "ResponseType": "Completed",
  "ConfirmationURL": "https://yourserver.com/webhooks/c2b/confirmation",
  "ValidationURL": "https://yourserver.com/webhooks/c2b/validation"
}
```

**Response:**
```json
{
  "ConversationID": "AG_20240514_123456",
  "OriginatorConversationID": "e713fa46-b90f-4ed5-a676-1b44cc30437e",
  "ResponseDescription": "success"
}
```

**Webhook Callbacks:**

**a) Validation Webhook** (`POST /webhooks/c2b/validation`)
```json
{
  "TransactionType": "Pay Bill Online",
  "TransID": "QHX01E60JV",
  "TransAmount": "500.00",
  "MSISDN": "254712345678",
  "AccountReference": "INV001",
  "TransTime": "20260514120000",
  "BusinessShortCode": "174379"
}
```

**Response (Webhook):**
```json
{
  "ResultCode": 0,
  "ResultDesc": "The service request has been processed successfully."
}
```

**b) Confirmation Webhook** (`POST /webhooks/c2b/confirmation`)
```json
{
  "TransactionType": "Pay Bill Online",
  "TransID": "QHX01E60JV",
  "TransAmount": 500,
  "MSISDN": "254712345678",
  "AccountReference": "INV001",
  "MpesaReceiptNumber": "QHX01E60JV",
  "TransactionDate": "2026-05-14T12:00:00+03:00",
  "BusinessShortCode": "174379"
}
```

---

### B2C (Business-to-Customer) APIs

#### 2. B2C Payment Request

```
POST /mpesa/b2c/v3/paymentrequest
Host: api.sandbox.safaricom.co.ke (sandbox)
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "InitiatorName": "TestInitiator",
  "SecurityCredential": "encrypted_credentials",
  "CommandID": "BusinessPayment",
  "Amount": 1000,
  "PartyA": "600123",
  "PartyB": "254712345678",
  "Remarks": "Refund payment",
  "QueueTimeOutURL": "https://yourserver.com/webhooks/b2c/timeout",
  "ResultURL": "https://yourserver.com/webhooks/b2c/result"
}
```

**Response:**
```json
{
  "ConversationID": "AG_20240514_789456",
  "OriginatorConversationID": "5c8c86f6-a7c2-406d-9ca3-fd0e2282f8de",
  "ResponseCode": "0",
  "ResponseDescription": "Accept the service request successfully."
}
```

**B2C Result Webhook** (`POST /webhooks/b2c/result`)
```json
{
  "Result": {
    "ResultType": 0,
    "ResultCode": 0,
    "ResultDesc": "The service request has been processed successfully.",
    "OriginatorConversationID": "5c8c86f6-a7c2-406d-9ca3-fd0e2282f8de",
    "ConversationID": "AG_20240514_789456",
    "TransactionID": "QHX01E60JV",
    "ReferenceData": {
      "ReferenceItem": {
        "Key": "DebitPartyCharges",
        "Value": "Mt:5.00|Cc:KES"
      }
    }
  }
}
```

---

### STK Push (Online Payment Prompts)

#### 3. STK Push Request

```
POST /mpesa/stkpush/v1/processrequest
Host: api.sandbox.safaricom.co.ke (sandbox)
Authorization: Bearer {access_token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "BusinessShortCode": "174379",
  "Password": "base64(174379passkey20260514120000)",
  "Timestamp": "20260514120000",
  "TransactionType": "CustomerPayBillOnline",
  "Amount": 1,
  "PartyA": "254712345678",
  "PartyB": "174379",
  "PhoneNumber": "254712345678",
  "CallBackURL": "https://yourserver.com/webhooks/stk/callback",
  "AccountReference": "INV001",
  "TransactionDesc": "Payment description"
}
```

**Password Generation:**
```
base64_encode("174379" + "passkey" + "20260514120000")
= "MjM2MzM3OjBkYTFlMjU3YjA2MzVmN2JiMGZmZjcxYWJjMmFlOGFk"
```

**Response:**
```json
{
  "MerchantRequestID": "29115-1590513-1",
  "CheckoutRequestID": "ws_CO_DMZ_12345_2738256c6228c",
  "ResponseCode": "0",
  "ResponseDescription": "Success. Request accepted for processing",
  "CustomerMessage": "Success. Request accepted for processing"
}
```

**STK Callback Webhook** (`POST /webhooks/stk/callback`)
```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-1590513-1",
      "CheckoutRequestID": "ws_CO_DMZ_12345_2738256c6228c",
      "ResultCode": 0,
      "ResultDesc": "The service request has been processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {"Name": "Amount", "Value": 1},
          {"Name": "MpesaReceiptNumber", "Value": "QHX01E60JV"},
          {"Name": "TransactionDate", "Value": 20260514120030},
          {"Name": "PhoneNumber", "Value": 254712345678}
        ]
      }
    }
  }
}
```

---

## Webhook Payload Examples

### C2B Validation Request (Incoming)

```json
{
  "TransactionType": "Pay Bill Online",
  "TransID": "STK123456789",
  "TransAmount": "5000.00",
  "MSISDN": "254712345678",
  "AccountReference": "CUST001",
  "TransTime": "20260514120000",
  "BusinessShortCode": "174379"
}
```

### C2B Validation Response (Our Server)

```json
{
  "ResultCode": 0,
  "ResultDesc": "The transaction has been validated successfully."
}
```

Error Response:
```json
{
  "ResultCode": 1,
  "ResultDesc": "Invalid account reference"
}
```

---

## Error Codes & Handling

### API Response Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Process normally |
| 1 | Insufficient Funds | Retry later |
| 2 | Less than minimum transaction allowed | Validation error |
| 3 | More than maximum transaction allowed | Validation error |
| 6 | Transaction has expired | Retry |
| 17 | System unavailable | Retry with exponential backoff |
| 500 | Internal server error | Retry later |
| 502 | Bad gateway | Retry later |
| 503 | Service unavailable | Retry later |

### HTTP Status Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 200 | OK | Process response |
| 400 | Bad Request | Fix request and retry |
| 401 | Unauthorized | Check credentials |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Verify URL |
| 408 | Request Timeout | Retry |
| 429 | Too Many Requests | Implement rate limiting |
| 500 | Internal Server Error | Retry with exponential backoff |
| 502 | Bad Gateway | Retry |
| 503 | Service Unavailable | Retry |

### Retry Strategy

```python
def retry_daraja_call(func, max_retries=3):
    for attempt in range(max_retries):
        try:
            return func()
        except TransientError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                sleep(wait_time)
            else:
                raise PermanentError(str(e))
        except PermanentError:
            raise  # Don't retry
```

---

## Configuration

### Environment Variables

```bash
# Daraja API Credentials
DARAJA_CONSUMER_KEY=xxxxxxxxxxxxxxxxxxxx
DARAJA_CONSUMER_SECRET=xxxxxxxxxxxxxxxxxxxx
DARAJA_BUSINESS_SHORTCODE=174379
DARAJA_PASSKEY=xxxxxxxxxxxxxxxxxxxx
DARAJA_ENVIRONMENT=sandbox  # or production

# Webhook Configuration
WEBHOOK_HOST=https://yourdomain.com
WEBHOOK_PORT=5000

# Daraja Endpoints (override if needed)
DARAJA_API_BASE_URL=https://api.sandbox.safaricom.co.ke
DARAJA_AUTH_ENDPOINT=/oauth/v1/generate
DARAJA_C2B_REGISTER_URL=/mpesa/c2b/v1/registerurl
DARAJA_STK_PUSH_URL=/mpesa/stkpush/v1/processrequest
DARAJA_B2C_URL=/mpesa/b2c/v3/paymentrequest
```

### Sandbox vs. Production

#### Sandbox Setup
```python
client = DarajaClient(
    consumer_key="YOUR_SANDBOX_KEY",
    consumer_secret="YOUR_SANDBOX_SECRET",
    business_shortcode="174379",
    passkey="bfb279f9aa9bdbcf158e97dd71a467cd",  # Daraja test passkey
    environment="sandbox"
)
```

#### Production Setup
```python
client = DarajaClient(
    consumer_key="YOUR_PRODUCTION_KEY",
    consumer_secret="YOUR_PRODUCTION_SECRET",
    business_shortcode="YOUR_BUSINESS_CODE",
    passkey=os.getenv("DARAJA_PRODUCTION_PASSKEY"),
    environment="production"
)
```

---

## Rate Limiting

### Daraja API Limits

- **Requests per second**: 100 req/sec
- **C2B transactions**: 1,000,000 per day
- **STK push**: 100,000 per day
- **Token validity**: 3600 seconds (1 hour)

### Our Implementation

```python
# Rate limiter configuration
RATE_LIMIT_CONFIG = {
    "webhook_requests": RateLimit(requests=1000, per_seconds=60),
    "daraja_api": RateLimit(requests=100, per_seconds=1),
    "stk_push": RateLimit(requests=100, per_seconds=60),
}
```

---

## Security Considerations

### Credential Management
- **Never** commit credentials to version control
- Use `.env` files (git-ignored) for local development
- Use secrets management (AWS Secrets Manager, HashiCorp Vault) for production
- Rotate credentials regularly

### Webhook Validation
```python
def validate_webhook_signature(request):
    """Validate webhook came from Safaricom."""
    # Daraja doesn't use signatures, but validate request origin
    # - Check IP whitelist
    # - Validate TLS certificate
    # - Check timestamp freshness (< 5 minutes)
    pass
```

### HTTPS Enforcement
- All webhook URLs must use HTTPS
- Valid certificate required (self-signed not accepted)
- TLS 1.2 minimum

### Data Privacy
- Don't log full phone numbers or transaction details
- Sanitize logs before sharing
- Implement encryption for PII (Personally Identifiable Information)
- Comply with Kenya's Data Protection Act (GDPI)

---

## Monitoring & Debugging

### Logging Configuration
```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log important events (but not sensitive data)
logger.info(f"Initiated STK push: {account_ref}")
logger.error(f"API error: {error_code} - {error_desc}")
```

### Common Issues & Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid/expired token | Check credentials, generate new token |
| Invalid phone number | Wrong format | Use 254XXXXXXXXX format |
| Transaction timeout | Network delay | Implement exponential backoff retry |
| Webhook not received | URL unreachable | Check HTTPS cert, firewall rules |
| High latency | Daraja API slow | Check network, implement caching |

---

## Testing

### Mock Responses (for unit tests)
```python
@pytest.fixture
def mock_daraja_response():
    return {
        "MerchantRequestID": "TEST_123",
        "CheckoutRequestID": "TEST_456",
        "ResponseCode": "0",
        "ResponseDescription": "Success"
    }
```

### Webhook Testing
```bash
# Test C2B validation
curl -X POST http://localhost:5000/webhooks/c2b/validation \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionType": "Pay Bill Online",
    "TransID": "TEST123",
    "TransAmount": "5000",
    "MSISDN": "254712345678",
    "AccountReference": "TEST",
    "TransTime": "20260514120000",
    "BusinessShortCode": "174379"
  }'
```

---

## References

- [Safaricom Daraja Documentation](https://developer.safaricom.co.ke/)
- [M-Pesa API Guide](https://developer.safaricom.co.ke/docs)
- [OAuth 2.0 RFC 6749](https://tools.ietf.org/html/rfc6749)
- [HTTP Status Codes](https://httpwg.org/specs/rfc7231.html#status.codes)
