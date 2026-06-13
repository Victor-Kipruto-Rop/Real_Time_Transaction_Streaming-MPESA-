# M-Pesa Analytics Platform - Examples

This directory contains example code and sample data for working with the M-Pesa Analytics Platform.

## Contents

### 1. Sample Data

- **`sample_transactions.json`** - Sample M-Pesa transaction payloads for testing

### 2. API Examples

- **`api_usage.py`** - Complete examples of using the REST API
  - Health checks
  - Transaction queries
  - Customer analytics
  - STK Push operations

### 3. Webhook Simulation

- **`webhook_simulation.py`** - Simulate M-Pesa webhook callbacks
  - C2B confirmation webhooks
  - C2B validation webhooks
  - STK Push callbacks
  - Load testing

## Quick Start

### Using the API Client

```python
from examples.api_usage import MPesaAnalyticsClient

# Initialize client
client = MPesaAnalyticsClient(
    base_url='http://localhost:5000',
    api_token='your_api_token_here'
)

# Check health
health = client.health_check()
print(health)

# Get daily summary
summary = client.get_daily_summary('2026-06-13')
print(summary)
```

### Simulating Webhooks

```python
from examples.webhook_simulation import WebhookSimulator

# Initialize simulator
simulator = WebhookSimulator('http://localhost:5000')

# Send a single transaction
response = simulator.send_c2b_confirmation()
print(f"Status: {response.status_code}")

# Simulate load (100 transactions)
simulator.simulate_load(num_transactions=100, delay=0.1)
```

### Testing with Sample Data

```bash
# Send sample transaction to webhook
curl -X POST http://localhost:5000/webhook/c2b/confirmation \
  -H "Content-Type: application/json" \
  -d @examples/sample_transactions.json
```

## Running Examples

### API Usage Examples

```bash
# Install dependencies
pip install requests

# Run API examples
python examples/api_usage.py
```

### Webhook Simulation

```bash
# Run webhook simulation
python examples/webhook_simulation.py

# Run specific example
python -c "from examples.webhook_simulation import example_load_test; example_load_test()"
```

## Use Cases

### 1. Development Testing

Use the webhook simulator to test your application without needing actual M-Pesa transactions:

```python
simulator = WebhookSimulator()
simulator.simulate_load(num_transactions=1000, delay=0.05)
```

### 2. Integration Testing

Test the complete flow from webhook to database:

```python
# Send validation
simulator.send_c2b_validation(payload)

# Send confirmation
simulator.send_c2b_confirmation(payload)

# Verify in database
client.get_transaction(payload['TransID'])
```

### 3. Load Testing

Stress test your system:

```python
# High load scenario
simulator.simulate_load(num_transactions=10000, delay=0.01)
```

### 4. API Integration

Integrate with your application:

```python
client = MPesaAnalyticsClient(base_url, token)

# Get analytics for dashboard
report = client.get_analytics_report(
    start_date='2026-06-01',
    end_date='2026-06-13'
)
```

## Configuration

### Environment Variables

Set these environment variables before running examples:

```bash
export MPESA_API_URL="http://localhost:5000"
export MPESA_API_TOKEN="your_api_token"
```

### Custom Configuration

Modify the examples to use your configuration:

```python
# api_usage.py
client = MPesaAnalyticsClient(
    base_url='https://api.your-domain.com',
    api_token='your_production_token'
)

# webhook_simulation.py
simulator = WebhookSimulator('https://api.your-domain.com')
```

## Best Practices

1. **Use Sample Data for Testing**: Always test with sample data before using production
2. **Rate Limiting**: Be aware of rate limits when simulating load
3. **Error Handling**: Implement proper error handling in your integration
4. **Logging**: Enable logging to debug issues
5. **Security**: Never commit API tokens to version control

## Troubleshooting

### Connection Refused

```bash
# Check if services are running
docker compose ps

# Start services
docker compose up -d
```

### Authentication Errors

```bash
# Verify API token
echo $MPESA_API_TOKEN

# Update token in .env
nano .env
```

### Rate Limiting

If you hit rate limits, reduce the load:

```python
# Reduce transactions or increase delay
simulator.simulate_load(num_transactions=100, delay=0.5)
```

## Additional Resources

- [API Documentation](../docs/API.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
- [Troubleshooting Guide](../docs/TROUBLESHOOTING.md)
- [Architecture Documentation](../docs/ARCHITECTURE.md)

## Support

For issues or questions:
- GitHub Issues: https://github.com/kipruto45/Real_Time_Transaction_Streaming-MPESA-/issues
- Email: support@your-domain.com
