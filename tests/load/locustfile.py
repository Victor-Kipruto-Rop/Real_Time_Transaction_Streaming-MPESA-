"""
Load testing for M-Pesa Analytics Platform using Locust
"""

from locust import HttpUser, task, between, events
import json
import random
from datetime import datetime


class MPesaWebhookUser(HttpUser):
    """Simulate M-Pesa webhook requests"""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self):
        """Initialize user session"""
        self.transaction_counter = 0

    @task(10)
    def send_c2b_confirmation(self):
        """Send C2B confirmation webhook (most common)"""
        self.transaction_counter += 1

        transaction_data = {
            "TransID": f'TXN{datetime.now().strftime("%Y%m%d%H%M%S")}{random.randint(1000, 9999)}',
            "TransAmount": str(random.randint(100, 10000)),
            "MSISDN": f"2547{random.randint(10000000, 99999999)}",
            "AccountReference": f"ACC{random.randint(1000, 9999)}",
            "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
            "BillRefNumber": f"BILL{random.randint(1000, 9999)}",
            "FirstName": random.choice(["John", "Jane", "Peter", "Mary", "David"]),
            "MiddleName": random.choice(["", "K", "M", "W"]),
            "LastName": random.choice(["Smith", "Doe", "Johnson", "Williams", "Brown"]),
            "OrgAccountBalance": str(random.randint(10000, 100000)),
        }

        with self.client.post(
            "/webhook/c2b/confirmation",
            json=transaction_data,
            catch_response=True,
            name="C2B Confirmation",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(5)
    def send_c2b_validation(self):
        """Send C2B validation webhook"""
        transaction_data = {
            "TransID": f'VAL{datetime.now().strftime("%Y%m%d%H%M%S")}{random.randint(1000, 9999)}',
            "TransAmount": str(random.randint(100, 10000)),
            "MSISDN": f"2547{random.randint(10000000, 99999999)}",
            "AccountReference": f"ACC{random.randint(1000, 9999)}",
            "TransTime": datetime.now().strftime("%Y%m%d%H%M%S"),
        }

        with self.client.post(
            "/webhook/c2b/validation",
            json=transaction_data,
            catch_response=True,
            name="C2B Validation",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(3)
    def send_stk_callback(self):
        """Send STK Push callback webhook"""
        callback_data = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": f"REQ{random.randint(10000, 99999)}",
                    "CheckoutRequestID": f"CHK{random.randint(10000, 99999)}",
                    "ResultCode": random.choice([0, 0, 0, 1032]),  # Mostly success
                    "ResultDesc": (
                        "Success" if random.random() > 0.1 else "User cancelled"
                    ),
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": random.randint(100, 5000)},
                            {
                                "Name": "MpesaReceiptNumber",
                                "Value": f"RCP{random.randint(10000, 99999)}",
                            },
                            {
                                "Name": "PhoneNumber",
                                "Value": f"2547{random.randint(10000000, 99999999)}",
                            },
                        ]
                    },
                }
            }
        }

        with self.client.post(
            "/webhook/stk/callback",
            json=callback_data,
            catch_response=True,
            name="STK Callback",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(1)
    def check_health(self):
        """Check health endpoint"""
        with self.client.get(
            "/health", catch_response=True, name="Health Check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(
                    f"Health check failed with status {response.status_code}"
                )


class MPesaAPIUser(HttpUser):
    """Simulate API requests to M-Pesa platform"""

    wait_time = between(2, 5)

    @task(5)
    def query_transaction(self):
        """Query transaction status"""
        transaction_id = f"TXN{random.randint(100000, 999999)}"

        with self.client.get(
            f"/api/transactions/{transaction_id}",
            catch_response=True,
            name="Query Transaction",
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(3)
    def get_daily_summary(self):
        """Get daily transaction summary"""
        date = datetime.now().strftime("%Y-%m-%d")

        with self.client.get(
            f"/api/summary/daily?date={date}", catch_response=True, name="Daily Summary"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")

    @task(2)
    def get_customer_transactions(self):
        """Get customer transaction history"""
        phone = f"2547{random.randint(10000000, 99999999)}"

        with self.client.get(
            f"/api/customers/{phone}/transactions",
            catch_response=True,
            name="Customer Transactions",
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Failed with status {response.status_code}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts"""
    print("=" * 60)
    print("M-Pesa Analytics Platform - Load Test Starting")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops"""
    print("=" * 60)
    print("M-Pesa Analytics Platform - Load Test Completed")
    print("=" * 60)

    # Print summary statistics
    stats = environment.stats
    print(f"\nTotal Requests: {stats.total.num_requests}")
    print(f"Total Failures: {stats.total.num_failures}")
    print(f"Average Response Time: {stats.total.avg_response_time:.2f}ms")
    print(f"Min Response Time: {stats.total.min_response_time:.2f}ms")
    print(f"Max Response Time: {stats.total.max_response_time:.2f}ms")
    print(f"Requests per Second: {stats.total.total_rps:.2f}")
    print(f"Failure Rate: {stats.total.fail_ratio * 100:.2f}%")
