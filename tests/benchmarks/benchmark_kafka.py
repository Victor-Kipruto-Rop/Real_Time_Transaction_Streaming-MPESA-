"""
Kafka Performance Benchmarks

Tests Kafka producer and consumer throughput and latency.
"""

import time
import statistics
from typing import List, Dict
from kafka import KafkaProducer, KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
import json
import pytest


class KafkaBenchmark:
    """Benchmark Kafka performance"""

    def __init__(self, bootstrap_servers: str = "localhost:9092"):
        self.bootstrap_servers = bootstrap_servers
        self.topic = "benchmark-test"

    def setup(self):
        """Setup test topic"""
        admin = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)

        # Delete topic if exists
        try:
            admin.delete_topics([self.topic])
            time.sleep(2)
        except:
            pass

        # Create topic
        topic = NewTopic(name=self.topic, num_partitions=3, replication_factor=1)
        admin.create_topics([topic])
        time.sleep(2)

    def teardown(self):
        """Cleanup test topic"""
        admin = KafkaAdminClient(bootstrap_servers=self.bootstrap_servers)
        try:
            admin.delete_topics([self.topic])
        except:
            pass

    def benchmark_producer_throughput(self, num_messages: int = 10000) -> Dict:
        """
        Benchmark producer throughput

        Args:
            num_messages: Number of messages to send

        Returns:
            Dict with benchmark results
        """
        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            compression_type="snappy",
            batch_size=16384,
            linger_ms=10,
        )

        message = {
            "transaction_id": "TXN123456789",
            "amount": 1000.00,
            "phone_number": "254712345678",
            "timestamp": time.time(),
        }

        start_time = time.time()

        for i in range(num_messages):
            message["transaction_id"] = f"TXN{i:010d}"
            producer.send(self.topic, value=message)

        producer.flush()
        end_time = time.time()

        duration = end_time - start_time
        throughput = num_messages / duration

        producer.close()

        return {
            "test": "producer_throughput",
            "messages": num_messages,
            "duration_seconds": round(duration, 2),
            "throughput_msg_per_sec": round(throughput, 2),
            "avg_latency_ms": round((duration / num_messages) * 1000, 2),
        }

    def benchmark_producer_latency(self, num_messages: int = 1000) -> Dict:
        """
        Benchmark producer latency

        Args:
            num_messages: Number of messages to send

        Returns:
            Dict with latency statistics
        """
        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        message = {
            "transaction_id": "TXN123456789",
            "amount": 1000.00,
            "phone_number": "254712345678",
        }

        latencies = []

        for i in range(num_messages):
            message["transaction_id"] = f"TXN{i:010d}"

            start = time.time()
            future = producer.send(self.topic, value=message)
            future.get(timeout=10)  # Wait for acknowledgment
            latency = (time.time() - start) * 1000  # Convert to ms

            latencies.append(latency)

        producer.close()

        return {
            "test": "producer_latency",
            "messages": num_messages,
            "avg_latency_ms": round(statistics.mean(latencies), 2),
            "median_latency_ms": round(statistics.median(latencies), 2),
            "p95_latency_ms": round(statistics.quantiles(latencies, n=20)[18], 2),
            "p99_latency_ms": round(statistics.quantiles(latencies, n=100)[98], 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
        }

    def benchmark_consumer_throughput(self, num_messages: int = 10000) -> Dict:
        """
        Benchmark consumer throughput

        Args:
            num_messages: Number of messages to consume

        Returns:
            Dict with benchmark results
        """
        # First, produce messages
        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        message = {
            "transaction_id": "TXN123456789",
            "amount": 1000.00,
            "phone_number": "254712345678",
        }

        for i in range(num_messages):
            message["transaction_id"] = f"TXN{i:010d}"
            producer.send(self.topic, value=message)

        producer.flush()
        producer.close()

        # Now consume
        consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id="benchmark-consumer",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        start_time = time.time()
        consumed = 0

        for message in consumer:
            consumed += 1
            if consumed >= num_messages:
                break

        end_time = time.time()
        duration = end_time - start_time
        throughput = consumed / duration

        consumer.close()

        return {
            "test": "consumer_throughput",
            "messages": consumed,
            "duration_seconds": round(duration, 2),
            "throughput_msg_per_sec": round(throughput, 2),
            "avg_latency_ms": round((duration / consumed) * 1000, 2),
        }

    def benchmark_end_to_end_latency(self, num_messages: int = 100) -> Dict:
        """
        Benchmark end-to-end latency (produce + consume)

        Args:
            num_messages: Number of messages to test

        Returns:
            Dict with latency statistics
        """
        consumer = KafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset="latest",
            enable_auto_commit=True,
            group_id="benchmark-e2e",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

        producer = KafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )

        latencies = []

        for i in range(num_messages):
            message = {
                "transaction_id": f"TXN{i:010d}",
                "amount": 1000.00,
                "timestamp": time.time(),
            }

            # Send message
            producer.send(self.topic, value=message)
            producer.flush()

            # Consume message
            for msg in consumer:
                receive_time = time.time()
                send_time = msg.value["timestamp"]
                latency = (receive_time - send_time) * 1000  # ms
                latencies.append(latency)
                break

        producer.close()
        consumer.close()

        return {
            "test": "end_to_end_latency",
            "messages": num_messages,
            "avg_latency_ms": round(statistics.mean(latencies), 2),
            "median_latency_ms": round(statistics.median(latencies), 2),
            "p95_latency_ms": round(statistics.quantiles(latencies, n=20)[18], 2),
            "p99_latency_ms": round(statistics.quantiles(latencies, n=100)[98], 2),
            "min_latency_ms": round(min(latencies), 2),
            "max_latency_ms": round(max(latencies), 2),
        }


def run_all_benchmarks():
    """Run all Kafka benchmarks"""
    benchmark = KafkaBenchmark()

    print("Setting up Kafka benchmark...")
    benchmark.setup()

    results = []

    try:
        print("\n1. Testing Producer Throughput...")
        result = benchmark.benchmark_producer_throughput(10000)
        results.append(result)
        print(json.dumps(result, indent=2))

        print("\n2. Testing Producer Latency...")
        result = benchmark.benchmark_producer_latency(1000)
        results.append(result)
        print(json.dumps(result, indent=2))

        print("\n3. Testing Consumer Throughput...")
        result = benchmark.benchmark_consumer_throughput(10000)
        results.append(result)
        print(json.dumps(result, indent=2))

        print("\n4. Testing End-to-End Latency...")
        result = benchmark.benchmark_end_to_end_latency(100)
        results.append(result)
        print(json.dumps(result, indent=2))

    finally:
        print("\nCleaning up...")
        benchmark.teardown()

    return results


if __name__ == "__main__":
    results = run_all_benchmarks()

    print("\n" + "=" * 60)
    print("KAFKA BENCHMARK SUMMARY")
    print("=" * 60)

    for result in results:
        print(f"\n{result['test'].upper()}:")
        for key, value in result.items():
            if key != "test":
                print(f"  {key}: {value}")
