"""
API Performance Benchmarks

Tests webhook receiver API performance and throughput.
"""

import time
import statistics
import requests
import json
from typing import Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import random


class APIBenchmark:
    """Benchmark API performance"""

    def __init__(self, base_url: str = "http://localhost:5000"):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json"}

    def benchmark_health_endpoint(self, num_requests: int = 1000) -> Dict:
        """
        Benchmark health check endpoint

        Args:
            num_requests: Number of requests to send

        Returns:
            Dict with benchmark results
        """
        response_times = []
        errors = 0

        for _ in range(num_requests):
            start = time.time()
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                duration = (time.time() - start) * 1000
                response_times.append(duration)

                if response.status_code != 200:
                    errors += 1
            except Exception:
                errors += 1

        return {
            "test": "health_endpoint",
            "requests": num_requests,
            "errors": errors,
            "success_rate": round((num_requests - errors) / num_requests * 100, 2),
            "avg_response_time_ms": round(statistics.mean(response_times), 2),
            "median_response_time_ms": round(statistics.median(response_times), 2),
            "p95_response_time_ms": round(
                statistics.quantiles(response_times, n=20)[18], 2
            ),
            "p99_response_time_ms": round(
                statistics.quantiles(response_times, n=100)[98], 2
            ),
            "min_response_time_ms": round(min(response_times), 2),
            "max_response_time_ms": round(max(response_times), 2),
        }

    def benchmark_webhook_endpoint(self, num_requests: int = 1000) -> Dict:
        """
        Benchmark C2B webhook endpoint

        Args:
            num_requests: Number of requests to send

        Returns:
            Dict with benchmark results
        """
        response_times = []
        errors = 0

        for i in range(num_requests):
            payload = {
                "TransID": f"TXN{i:010d}",
                "TransAmount": str(random.uniform(100, 10000)),
                "MSISDN": f"25471234{i % 10000:04d}",
                "AccountReference": f"ACC{i % 100:03d}",
                "TransTime": "20260613120000",
                "BillRefNumber": f"BILL{i % 100:03d}",
                "FirstName": "John",
                "LastName": "Doe",
            }

            start = time.time()
            try:
                response = requests.post(
                    f"{self.base_url}/webhook/c2b/confirmation",
                    json=payload,
                    headers=self.headers,
                    timeout=10,
                )
                duration = (time.time() - start) * 1000
                response_times.append(duration)

                if response.status_code not in [200, 409]:  # 409 is duplicate
                    errors += 1
            except Exception:
                errors += 1

        return {
            "test": "webhook_endpoint",
            "requests": num_requests,
            "errors": errors,
            "success_rate": round((num_requests - errors) / num_requests * 100, 2),
            "avg_response_time_ms": round(statistics.mean(response_times), 2),
            "median_response_time_ms": round(statistics.median(response_times), 2),
            "p95_response_time_ms": round(
                statistics.quantiles(response_times, n=20)[18], 2
            ),
            "p99_response_time_ms": round(
                statistics.quantiles(response_times, n=100)[98], 2
            ),
            "throughput_rps": round(num_requests / (sum(response_times) / 1000), 2),
        }

    def benchmark_concurrent_requests(
        self, num_requests: int = 1000, concurrency: int = 10
    ) -> Dict:
        """
        Benchmark concurrent requests

        Args:
            num_requests: Total number of requests
            concurrency: Number of concurrent workers

        Returns:
            Dict with benchmark results
        """
        response_times = []
        errors = 0

        def send_request(request_id):
            payload = {
                "TransID": f"TXN{request_id:010d}",
                "TransAmount": str(random.uniform(100, 10000)),
                "MSISDN": f"25471234{request_id % 10000:04d}",
                "AccountReference": f"ACC{request_id % 100:03d}",
                "TransTime": "20260613120000",
            }

            start = time.time()
            try:
                response = requests.post(
                    f"{self.base_url}/webhook/c2b/confirmation",
                    json=payload,
                    headers=self.headers,
                    timeout=10,
                )
                duration = (time.time() - start) * 1000
                return duration, response.status_code in [200, 409]
            except Exception:
                return 0, False

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(send_request, i) for i in range(num_requests)]

            for future in as_completed(futures):
                duration, success = future.result()
                if success:
                    response_times.append(duration)
                else:
                    errors += 1

        total_time = time.time() - start_time

        return {
            "test": "concurrent_requests",
            "total_requests": num_requests,
            "concurrency": concurrency,
            "errors": errors,
            "success_rate": round((num_requests - errors) / num_requests * 100, 2),
            "total_time_seconds": round(total_time, 2),
            "throughput_rps": round(num_requests / total_time, 2),
            "avg_response_time_ms": round(statistics.mean(response_times), 2),
            "p95_response_time_ms": round(
                statistics.quantiles(response_times, n=20)[18], 2
            ),
            "p99_response_time_ms": round(
                statistics.quantiles(response_times, n=100)[98], 2
            ),
        }

    def benchmark_rate_limiting(
        self, requests_per_second: int = 150, duration_seconds: int = 10
    ) -> Dict:
        """
        Test rate limiting behavior

        Args:
            requests_per_second: Target RPS
            duration_seconds: Test duration

        Returns:
            Dict with rate limiting results
        """
        total_requests = 0
        rate_limited = 0
        successful = 0

        start_time = time.time()
        end_time = start_time + duration_seconds

        while time.time() < end_time:
            batch_start = time.time()

            for _ in range(requests_per_second):
                payload = {
                    "TransID": f"TXN{total_requests:010d}",
                    "TransAmount": "1000",
                    "MSISDN": "254712345678",
                    "TransTime": "20260613120000",
                }

                try:
                    response = requests.post(
                        f"{self.base_url}/webhook/c2b/confirmation",
                        json=payload,
                        headers=self.headers,
                        timeout=5,
                    )

                    total_requests += 1

                    if response.status_code == 429:
                        rate_limited += 1
                    elif response.status_code in [200, 409]:
                        successful += 1

                except Exception:
                    total_requests += 1

            # Sleep to maintain target RPS
            elapsed = time.time() - batch_start
            if elapsed < 1.0:
                time.sleep(1.0 - elapsed)

        return {
            "test": "rate_limiting",
            "target_rps": requests_per_second,
            "duration_seconds": duration_seconds,
            "total_requests": total_requests,
            "successful": successful,
            "rate_limited": rate_limited,
            "rate_limit_percentage": round(rate_limited / total_requests * 100, 2),
            "actual_rps": round(total_requests / duration_seconds, 2),
        }


def run_all_benchmarks():
    """Run all API benchmarks"""
    benchmark = APIBenchmark()

    results = []

    print("1. Testing Health Endpoint...")
    result = benchmark.benchmark_health_endpoint(1000)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n2. Testing Webhook Endpoint...")
    result = benchmark.benchmark_webhook_endpoint(1000)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n3. Testing Concurrent Requests (10 workers)...")
    result = benchmark.benchmark_concurrent_requests(1000, 10)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n4. Testing Concurrent Requests (50 workers)...")
    result = benchmark.benchmark_concurrent_requests(1000, 50)
    results.append(result)
    print(json.dumps(result, indent=2))

    print("\n5. Testing Rate Limiting...")
    result = benchmark.benchmark_rate_limiting(150, 10)
    results.append(result)
    print(json.dumps(result, indent=2))

    return results


if __name__ == "__main__":
    results = run_all_benchmarks()

    print("\n" + "=" * 60)
    print("API BENCHMARK SUMMARY")
    print("=" * 60)

    for result in results:
        print(f"\n{result['test'].upper()}:")
        for key, value in result.items():
            if key != "test":
                print(f"  {key}: {value}")
