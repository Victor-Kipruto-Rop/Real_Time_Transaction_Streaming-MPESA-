"""
Load Testing for M-Pesa Platform
Tests system under high load (1000+ concurrent users, 1000+ RPS)
Run with: locust -f tests/load/locustfile.py --headless -u 1000 -r 50 -t 1h
"""

import random
import time
import hmac
import hashlib
import json
from locust import HttpUser, task, between, events
import logging

logger = logging.getLogger(__name__)


class M_PesaLoadTestUser(HttpUser):
    """Simulates M-Pesa platform users under load"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Initialize user with test data"""
        self.base_url = "http://localhost:8000/api/v1"
        self.phone_numbers = [
            f"2547{random.randint(10000000, 99999999)}" for _ in range(100)
        ]
        self.transaction_ids = []
        self.checkout_request_ids = []

    @task(2)
    def health_check(self):
        """Test health endpoint (low weight)"""
        self.client.get(f"{self.base_url}/health", name="/health")

    @task(3)
    def get_transactions(self):
        """Get transactions with pagination"""
        phone = random.choice(self.phone_numbers)
        params = {
            "phone_number": phone,
            "status": random.choice(["success", "pending", "failed"]),
            "limit": random.choice([10, 50, 100]),
            "offset": random.randint(0, 1000),
        }
        self.client.get(
            f"{self.base_url}/transactions", params=params, name="/transactions"
        )

    @task(5)
    def initiate_stk_push(self):
        """Initiate STK push payment"""
        phone = random.choice(self.phone_numbers)
        amount = random.choice([50, 100, 500, 1000, 5000])

        payload = {
            "phone_number": phone,
            "amount": amount,
            "account_reference": "ChamaNdoto",
            "description": f"Test payment {int(time.time())}",
        }

        # Generate HMAC signature
        body_str = json.dumps(payload)
        signature = hmac.new(
            b"test-secret", body_str.encode(), hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Safaricom-Signature": signature,
            "Content-Type": "application/json",
        }

        response = self.client.post(
            f"{self.base_url}/transactions/initiate-stk",
            json=payload,
            headers=headers,
            name="/transactions/initiate-stk",
        )

        if response.status_code == 200:
            try:
                data = response.json()
                if "checkout_request_id" in data:
                    self.checkout_request_ids.append(data["checkout_request_id"])
            except Exception:
                pass

    @task(2)
    def query_stk_status(self):
        """Query STK push status"""
        if self.checkout_request_ids:
            checkout_id = random.choice(self.checkout_request_ids)
            self.client.get(
                f"{self.base_url}/transactions/stk/{checkout_id}/status",
                name="/transactions/stk/{id}/status",
            )

    @task(1)
    def get_customer_analytics(self):
        """Get customer analytics"""
        phone = random.choice(self.phone_numbers)
        self.client.get(
            f"{self.base_url}/analytics/customer/{phone}",
            name="/analytics/customer/{phone}",
        )

    @task(2)
    def get_fraud_alerts(self):
        """Get fraud alerts"""
        severity = random.choice(["low", "medium", "high", "critical"])
        params = {
            "severity": severity,
            "status": random.choice(["active", "resolved"]),
            "limit": 50,
        }
        self.client.get(
            f"{self.base_url}/analytics/fraud-alerts",
            params=params,
            name="/analytics/fraud-alerts",
        )

    @task(1)
    def get_analytics_summary(self):
        """Get analytics summary"""
        period = random.choice(["today", "week", "month", "year"])
        params = {"period": period}
        self.client.get(
            f"{self.base_url}/analytics/summary",
            params=params,
            name="/analytics/summary",
        )

    @task(2)
    def webhook_c2b_confirmation(self):
        """Simulate C2B confirmation webhook"""
        payload = {
            "TransactionType": "Pay Bills Online",
            "TransID": f"LHG{int(time.time() * 1000) % 1000000:06d}",
            "TransTime": time.strftime("%Y%m%d%H%M%S"),
            "TransAmount": random.choice([100, 500, 1000]),
            "BusinessShortCode": "8759693",
            "BillRefNumber": "ChamaNdoto",
            "FirstName": "Test",
            "LastName": "User",
            "MSISDN": random.choice(self.phone_numbers),
        }

        # Generate signature
        body_str = json.dumps(payload)
        signature = hmac.new(
            b"test-secret", body_str.encode(), hashlib.sha256
        ).hexdigest()

        headers = {
            "X-Safaricom-Signature": signature,
            "Content-Type": "application/json",
        }

        self.client.post(
            f"{self.base_url}/webhooks/c2b/confirmation",
            json=payload,
            headers=headers,
            name="/webhooks/c2b/confirmation",
        )

    @task(1)
    def get_transaction_detail(self):
        """Get individual transaction detail"""
        if self.transaction_ids:
            txn_id = random.choice(self.transaction_ids)
            self.client.get(
                f"{self.base_url}/transactions/{txn_id}", name="/transactions/{id}"
            )


class StressTestUser(HttpUser):
    """High-stress test user - minimal wait time"""

    wait_time = between(0.1, 0.5)

    def on_start(self):
        self.base_url = "http://localhost:8000/api/v1"

    @task
    def rapid_health_checks(self):
        """Rapid health checks to stress the system"""
        self.client.get(f"{self.base_url}/health", name="/health")

    @task(2)
    def rapid_transaction_queries(self):
        """Rapid transaction queries"""
        phone = f"2547{random.randint(10000000, 99999999)}"
        self.client.get(
            f"{self.base_url}/transactions",
            params={"phone_number": phone, "limit": 10},
            name="/transactions",
        )


# ============================================================================
# EVENT HANDLERS FOR MONITORING
# ============================================================================


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    logger.info("=" * 70)
    logger.info("LOAD TEST STARTED")
    logger.info(f"Target: {environment.host}")
    logger.info(f"Total users: {sum(u.count for u in environment.user_classes)}")
    logger.info("=" * 70)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    logger.info("=" * 70)
    logger.info("LOAD TEST COMPLETED")
    logger.info("=" * 70)


@events.request.add_listener
def on_request(
    request_type,
    name,
    response_time,
    response_length,
    response,
    context,
    exception,
    **kwargs,
):
    """Track individual request metrics"""

    if exception:
        logger.warning(f"Failed: {name} - {exception}")

    # Track slow requests (> 1000ms)
    if response_time > 1000:
        logger.warning(f"Slow request: {name} took {response_time}ms")


@events.locust_error_occurred.add_listener
def on_locust_error(locust_instance, exception, tb, **kwargs):
    """Track Locust errors"""
    logger.error(f"Error in {locust_instance.__class__.__name__}: {exception}")


# ============================================================================
# LOAD TEST SCENARIOS
# ============================================================================

"""
Run different load test scenarios:

1. BASELINE TEST (Normal load)
   locust -f tests/load/locustfile.py -u 100 -r 10 -t 10m

2. PEAK LOAD TEST (1000+ concurrent users)
   locust -f tests/load/locustfile.py -u 1000 -r 50 -t 30m

3. STRESS TEST (Push beyond limits)
   locust -f tests/load/locustfile.py -u 2000 -r 100 -t 15m

4. SPIKE TEST (Sudden traffic spike)
   locust -f tests/load/locustfile.py -u 100 -r 10 -t 2m --headless
   # Then spike to 1000 users in Locust UI

5. SUSTAINED LOAD (24-hour soak test)
   locust -f tests/load/locustfile.py -u 500 -r 25 -t 24h --headless

PERFORMANCE TARGETS:
- Response time p50: < 100ms
- Response time p95: < 500ms
- Response time p99: < 1000ms
- Error rate: < 1%
- Throughput: >= 1000 RPS
- System uptime: >= 99.95%

METRICS TO MONITOR:
1. Response times (min, max, avg, median, p95, p99)
2. Request count per endpoint
3. Error rate by endpoint
4. Failure reasons
5. Database connection pool usage
6. Kafka lag
7. CPU/Memory usage
8. Network throughput
"""
