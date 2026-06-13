# M-Pesa Analytics Platform - API Documentation

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Webhook Endpoints](#webhook-endpoints)
- [Query Endpoints](#query-endpoints)
- [Admin Endpoints](#admin-endpoints)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Examples](#examples)

## Overview

The M-Pesa Analytics Platform provides REST APIs for:
- Receiving M-Pesa transaction webhooks
- Querying transaction data
- Retrieving analytics and reports
- Managing system configuration

## Authentication

### API Token Authentication

Most endpoints require authentication using Bearer tokens:

```http
Authorization: Bearer YOUR_API_TOKEN
```

Configure your token in `.env`:
```bash
UI_TOKEN=your_secure_token_here
```

### Webhook Authentication

Webhook endpoints use IP whitelisting and signature verification for security.

## Base URL

**Development**: `http://localhost:5000`
**Production**: `https://your-domain.com`

---

## Webhook Endpoints

### 1. Health Check

Check system health status.

**Endpoint**: `GET /health`

**Authentication**: None

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2026-06-13T10:00:00Z",
  "services": {
    "database": "up",
    "kafka": "up",
    "redis": "up"
  }
}
```

**Status Codes**:
- `200 OK` - System healthy
- `503 Service Unavailable` - System unhealthy

---

### 2. C2B Confirmation Webhook

Receive C2B transaction confirmation from Safaricom.

**Endpoint**: `POST /webhook/c2b/confirmation`

**Authentication**: IP Whitelist + Signature

**Request Body**:
```json
{
  "TransID": "TXN123456789",
  "TransAmount": "1000.00",
  "MSISDN": "254712345678",
  "AccountReference": "ACC001",
  "TransTime": "20260613120000",
  "BillRefNumber": "BILL001",
  "FirstName": "John",
  "MiddleName": "K",
  "LastName": "Doe",
  "OrgAccountBalance": "50000.00"
}
```

**Response**:
```json
{
  "ResultCode": 0,
  "ResultDesc": "Accepted"
}
```

**Status Codes**:
- `200 OK` - Transaction accepted
- `400 Bad Request` - Invalid payload
- `409 Conflict` - Duplicate transaction
- `429 Too Many Requests` - Rate limit exceeded

---

### 3. C2B Validation Webhook

Validate C2B transaction before processing.

**Endpoint**: `POST /webhook/c2b/validation`

**Authentication**: IP Whitelist + Signature

**Request Body**:
```json
{
  "TransID": "TXN123456789",
  "TransAmount": "1000.00",
  "MSISDN": "254712345678",
  "AccountReference": "ACC001",
  "TransTime": "20260613120000"
}
```

**Response**:
```json
{
  "ResultCode": 0,
  "ResultDesc": "Accepted"
}
```

**Rejection Response**:
```json
{
  "ResultCode": 1,
  "ResultDesc": "Rejected - Invalid account"
}
```

---

### 4. STK Push Callback

Receive STK Push payment callback.

**Endpoint**: `POST /webhook/stk/callback`

**Authentication**: IP Whitelist

**Request Body**:
```json
{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "REQ12345",
      "CheckoutRequestID": "CHK12345",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {
            "Name": "Amount",
            "Value": 1000
          },
          {
            "Name": "MpesaReceiptNumber",
            "Value": "RCP12345"
          },
          {
            "Name": "PhoneNumber",
            "Value": 254712345678
          }
        ]
      }
    }
  }
}
```

**Response**:
```json
{
  "ResultCode": 0,
  "ResultDesc": "Success"
}
```

---

## Query Endpoints

### 5. Get Transaction by ID

Retrieve a specific transaction.

**Endpoint**: `GET /api/transactions/{transaction_id}`

**Authentication**: Bearer Token

**Parameters**:
- `transaction_id` (path) - Transaction ID

**Response**:
```json
{
  "transaction_id": "TXN123456789",
  "amount": 1000.00,
  "phone_number": "254712345678",
  "account_reference": "ACC001",
  "transaction_time": "2026-06-13T12:00:00Z",
  "status": "completed",
  "customer_name": "John K Doe"
}
```

**Status Codes**:
- `200 OK` - Transaction found
- `404 Not Found` - Transaction not found
- `401 Unauthorized` - Invalid token

---

### 6. List Transactions

List transactions with filtering and pagination.

**Endpoint**: `GET /api/transactions`

**Authentication**: Bearer Token

**Query Parameters**:
- `start_date` (optional) - Start date (YYYY-MM-DD)
- `end_date` (optional) - End date (YYYY-MM-DD)
- `phone_number` (optional) - Filter by phone number
- `min_amount` (optional) - Minimum amount
- `max_amount` (optional) - Maximum amount
- `page` (optional, default: 1) - Page number
- `limit` (optional, default: 50, max: 1000) - Results per page

**Example Request**:
```http
GET /api/transactions?start_date=2026-06-01&end_date=2026-06-13&limit=100
```

**Response**:
```json
{
  "data": [
    {
      "transaction_id": "TXN123456789",
      "amount": 1000.00,
      "phone_number": "254712345678",
      "transaction_time": "2026-06-13T12:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 100,
    "total": 1500,
    "pages": 15
  }
}
```

---

### 7. Get Daily Summary

Get daily transaction summary.

**Endpoint**: `GET /api/summary/daily`

**Authentication**: Bearer Token

**Query Parameters**:
- `date` (required) - Date (YYYY-MM-DD)

**Response**:
```json
{
  "date": "2026-06-13",
  "total_transactions": 1500,
  "total_amount": 1500000.00,
  "average_amount": 1000.00,
  "unique_customers": 850,
  "peak_hour": 14,
  "success_rate": 98.5
}
```

---

### 8. Get Customer Transactions

Get transaction history for a customer.

**Endpoint**: `GET /api/customers/{phone_number}/transactions`

**Authentication**: Bearer Token

**Parameters**:
- `phone_number` (path) - Customer phone number

**Query Parameters**:
- `limit` (optional, default: 50) - Number of results

**Response**:
```json
{
  "phone_number": "254712345678",
  "customer_name": "John K Doe",
  "total_transactions": 45,
  "total_amount": 45000.00,
  "transactions": [
    {
      "transaction_id": "TXN123456789",
      "amount": 1000.00,
      "transaction_time": "2026-06-13T12:00:00Z",
      "account_reference": "ACC001"
    }
  ]
}
```

---

### 9. Get Analytics Report

Get comprehensive analytics report.

**Endpoint**: `GET /api/analytics/report`

**Authentication**: Bearer Token

**Query Parameters**:
- `start_date` (required) - Start date
- `end_date` (required) - End date
- `metrics` (optional) - Comma-separated metrics (volume,customers,trends)

**Response**:
```json
{
  "period": {
    "start": "2026-06-01",
    "end": "2026-06-13"
  },
  "summary": {
    "total_transactions": 15000,
    "total_volume": 15000000.00,
    "unique_customers": 5000,
    "average_transaction": 1000.00
  },
  "trends": {
    "daily_growth": 5.2,
    "customer_growth": 3.8
  },
  "top_customers": [
    {
      "phone_number": "254712345678",
      "transaction_count": 150,
      "total_amount": 150000.00
    }
  ]
}
```

---

## Admin Endpoints

### 10. Initiate STK Push

Initiate STK Push payment request.

**Endpoint**: `POST /api/stk-push`

**Authentication**: Bearer Token

**Request Body**:
```json
{
  "phone_number": "254712345678",
  "amount": 100,
  "account_reference": "ACC001",
  "transaction_desc": "Payment for services"
}
```

**Response**:
```json
{
  "MerchantRequestID": "REQ12345",
  "CheckoutRequestID": "CHK12345",
  "ResponseCode": "0",
  "ResponseDescription": "Success. Request accepted for processing",
  "CustomerMessage": "Success. Request accepted for processing"
}
```

---

### 11. Query STK Push Status

Check STK Push payment status.

**Endpoint**: `GET /api/stk-push/{checkout_request_id}`

**Authentication**: Bearer Token

**Parameters**:
- `checkout_request_id` (path) - Checkout Request ID

**Response**:
```json
{
  "CheckoutRequestID": "CHK12345",
  "ResultCode": "0",
  "ResultDesc": "The service request is processed successfully.",
  "Amount": 100,
  "MpesaReceiptNumber": "RCP12345"
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid transaction amount",
    "details": {
      "field": "amount",
      "reason": "Amount must be positive"
    }
  }
}
```

### Error Codes

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Request validation failed |
| `UNAUTHORIZED` | Authentication failed |
| `FORBIDDEN` | Insufficient permissions |
| `NOT_FOUND` | Resource not found |
| `DUPLICATE_TRANSACTION` | Transaction already exists |
| `RATE_LIMIT_EXCEEDED` | Too many requests |
| `INTERNAL_ERROR` | Server error |
| `SERVICE_UNAVAILABLE` | Service temporarily unavailable |

---

## Rate Limiting

### Limits

- **Webhook Endpoints**: 120 requests/minute per IP
- **Query Endpoints**: 60 requests/minute per token
- **Admin Endpoints**: 30 requests/minute per token

### Rate Limit Headers

```http
X-RateLimit-Limit: 120
X-RateLimit-Remaining: 115
X-RateLimit-Reset: 1686654000
```

### Rate Limit Exceeded Response

```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "retry_after": 60
  }
}
```

---

## Examples

### Python Example

```python
import requests

# Configuration
BASE_URL = "http://localhost:5000"
API_TOKEN = "your_api_token"

headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Get daily summary
response = requests.get(
    f"{BASE_URL}/api/summary/daily",
    params={"date": "2026-06-13"},
    headers=headers
)

if response.status_code == 200:
    data = response.json()
    print(f"Total Transactions: {data['total_transactions']}")
    print(f"Total Amount: KES {data['total_amount']}")
else:
    print(f"Error: {response.status_code}")
```

### cURL Example

```bash
# Get transaction by ID
curl -X GET \
  http://localhost:5000/api/transactions/TXN123456789 \
  -H "Authorization: Bearer your_api_token"

# Initiate STK Push
curl -X POST \
  http://localhost:5000/api/stk-push \
  -H "Authorization: Bearer your_api_token" \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "254712345678",
    "amount": 100,
    "account_reference": "ACC001",
    "transaction_desc": "Payment"
  }'
```

### JavaScript Example

```javascript
const BASE_URL = 'http://localhost:5000';
const API_TOKEN = 'your_api_token';

// Get customer transactions
async function getCustomerTransactions(phoneNumber) {
  const response = await fetch(
    `${BASE_URL}/api/customers/${phoneNumber}/transactions`,
    {
      headers: {
        'Authorization': `Bearer ${API_TOKEN}`
      }
    }
  );
  
  if (response.ok) {
    const data = await response.json();
    console.log(`Total Transactions: ${data.total_transactions}`);
    return data;
  } else {
    console.error(`Error: ${response.status}`);
  }
}

getCustomerTransactions('254712345678');
```

---

## Webhooks Testing

### Test C2B Confirmation

```bash
curl -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H "Content-Type: application/json" \
  -d '{
    "TransID": "TXN123456789",
    "TransAmount": "1000",
    "MSISDN": "254712345678",
    "AccountReference": "ACC001",
    "TransTime": "20260613120000",
    "BillRefNumber": "BILL001",
    "FirstName": "John",
    "LastName": "Doe"
  }'
```

---

## Support

For API support:
- Email: api-support@your-domain.com
- Documentation: https://docs.your-domain.com
- GitHub Issues: https://github.com/kipruto45/Real_Time_Transaction_Streaming-MPESA-/issues
