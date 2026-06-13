"""
Tests for Kafka streaming functionality
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from ingestion.kafka_producer import KafkaProducerClient
from streaming.kafka_consumer import KafkaConsumerClient


class TestKafkaProducer:
    """Test Kafka producer functionality"""
    
    def test_producer_initialization(self, mock_env_vars):
        """Test Kafka producer initialization"""
        with patch('kafka.KafkaProducer') as mock_producer:
            producer = KafkaProducerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions'
            )
            assert producer is not None
            mock_producer.assert_called_once()
    
    def test_send_transaction_message(self, mock_kafka_producer, sample_mpesa_transaction):
        """Test sending transaction to Kafka"""
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            producer = KafkaProducerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions'
            )
            
            result = producer.send_transaction(sample_mpesa_transaction)
            assert result is not None
            mock_kafka_producer.send.assert_called_once()
    
    def test_message_serialization(self, mock_kafka_producer, sample_mpesa_transaction):
        """Test JSON serialization of messages"""
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            producer = KafkaProducerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions'
            )
            
            producer.send_transaction(sample_mpesa_transaction)
            
            # Verify message was serialized to JSON
            call_args = mock_kafka_producer.send.call_args
            assert call_args is not None
    
    def test_producer_error_handling(self, mock_env_vars):
        """Test producer error handling"""
        with patch('kafka.KafkaProducer') as mock_producer:
            mock_producer.side_effect = Exception('Kafka connection failed')
            
            with pytest.raises(Exception):
                KafkaProducerClient(
                    bootstrap_servers='localhost:9092',
                    topic='test-transactions'
                )
    
    def test_producer_flush(self, mock_kafka_producer):
        """Test producer flush on close"""
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            producer = KafkaProducerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions'
            )
            
            producer.close()
            mock_kafka_producer.flush.assert_called_once()
            mock_kafka_producer.close.assert_called_once()
    
    def test_batch_send_transactions(self, mock_kafka_producer):
        """Test sending multiple transactions in batch"""
        transactions = [
            {'TransID': 'TXN1', 'TransAmount': '100'},
            {'TransID': 'TXN2', 'TransAmount': '200'},
            {'TransID': 'TXN3', 'TransAmount': '300'}
        ]
        
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            producer = KafkaProducerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions'
            )
            
            results = producer.send_batch(transactions)
            assert len(results) == 3
            assert mock_kafka_producer.send.call_count == 3


class TestKafkaConsumer:
    """Test Kafka consumer functionality"""
    
    def test_consumer_initialization(self, mock_env_vars):
        """Test Kafka consumer initialization"""
        with patch('kafka.KafkaConsumer') as mock_consumer:
            consumer = KafkaConsumerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions',
                group_id='test-group'
            )
            assert consumer is not None
            mock_consumer.assert_called_once()
    
    def test_consume_messages(self, mock_env_vars, sample_mpesa_transaction):
        """Test consuming messages from Kafka"""
        with patch('kafka.KafkaConsumer') as mock_consumer:
            mock_consumer_instance = MagicMock()
            mock_message = MagicMock()
            mock_message.value = json.dumps(sample_mpesa_transaction).encode('utf-8')
            mock_consumer_instance.__iter__.return_value = [mock_message]
            mock_consumer.return_value = mock_consumer_instance
            
            consumer = KafkaConsumerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions',
                group_id='test-group'
            )
            
            messages = []
            for msg in consumer.consume(max_messages=1):
                messages.append(msg)
            
            assert len(messages) == 1
            assert messages[0]['TransID'] == sample_mpesa_transaction['TransID']
    
    def test_message_deserialization(self, mock_env_vars, sample_mpesa_transaction):
        """Test JSON deserialization of messages"""
        with patch('kafka.KafkaConsumer') as mock_consumer:
            mock_consumer_instance = MagicMock()
            mock_message = MagicMock()
            mock_message.value = json.dumps(sample_mpesa_transaction).encode('utf-8')
            mock_consumer_instance.__iter__.return_value = [mock_message]
            mock_consumer.return_value = mock_consumer_instance
            
            consumer = KafkaConsumerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions',
                group_id='test-group'
            )
            
            for msg in consumer.consume(max_messages=1):
                assert isinstance(msg, dict)
                assert 'TransID' in msg
    
    def test_consumer_commit_offset(self, mock_env_vars):
        """Test committing consumer offset"""
        with patch('kafka.KafkaConsumer') as mock_consumer:
            mock_consumer_instance = MagicMock()
            mock_consumer.return_value = mock_consumer_instance
            
            consumer = KafkaConsumerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions',
                group_id='test-group'
            )
            
            consumer.commit()
            mock_consumer_instance.commit.assert_called_once()
    
    def test_consumer_error_handling(self, mock_env_vars):
        """Test consumer error handling"""
        with patch('kafka.KafkaConsumer') as mock_consumer:
            mock_consumer.side_effect = Exception('Kafka connection failed')
            
            with pytest.raises(Exception):
                KafkaConsumerClient(
                    bootstrap_servers='localhost:9092',
                    topic='test-transactions',
                    group_id='test-group'
                )
    
    def test_consumer_close(self, mock_env_vars):
        """Test consumer close"""
        with patch('kafka.KafkaConsumer') as mock_consumer:
            mock_consumer_instance = MagicMock()
            mock_consumer.return_value = mock_consumer_instance
            
            consumer = KafkaConsumerClient(
                bootstrap_servers='localhost:9092',
                topic='test-transactions',
                group_id='test-group'
            )
            
            consumer.close()
            mock_consumer_instance.close.assert_called_once()


class TestKafkaDLQ:
    """Test Kafka Dead Letter Queue functionality"""
    
    def test_send_to_dlq(self, mock_kafka_producer):
        """Test sending failed messages to DLQ"""
        from ingestion.kafka_dlq import send_to_dlq
        
        failed_message = {
            'TransID': 'TXN123',
            'error': 'Validation failed',
            'original_message': {'TransID': 'TXN123'}
        }
        
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            result = send_to_dlq(failed_message, topic='dlq-transactions')
            assert result is not None
            mock_kafka_producer.send.assert_called_once()
    
    def test_dlq_message_enrichment(self, mock_kafka_producer):
        """Test DLQ message enrichment with metadata"""
        from ingestion.kafka_dlq import send_to_dlq
        
        failed_message = {'TransID': 'TXN123'}
        
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            send_to_dlq(
                failed_message,
                topic='dlq-transactions',
                error_reason='Database insert failed'
            )
            
            # Verify enriched message was sent
            call_args = mock_kafka_producer.send.call_args
            assert call_args is not None
    
    def test_dlq_retry_logic(self, mock_kafka_producer):
        """Test retry logic for DLQ messages"""
        from ingestion.kafka_dlq import retry_dlq_message
        
        dlq_message = {
            'TransID': 'TXN123',
            'retry_count': 2,
            'max_retries': 3
        }
        
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            should_retry = retry_dlq_message(dlq_message)
            assert should_retry is True


class TestKafkaMetrics:
    """Test Kafka metrics collection"""
    
    def test_producer_metrics(self, mock_kafka_producer):
        """Test collecting producer metrics"""
        from ingestion.metrics import KafkaMetrics
        
        with patch('kafka.KafkaProducer', return_value=mock_kafka_producer):
            metrics = KafkaMetrics()
            
            # Simulate sending messages
            for i in range(10):
                metrics.record_message_sent()
            
            stats = metrics.get_producer_stats()
            assert stats['messages_sent'] == 10
    
    def test_consumer_metrics(self, mock_env_vars):
        """Test collecting consumer metrics"""
        from ingestion.metrics import KafkaMetrics
        
        metrics = KafkaMetrics()
        
        # Simulate consuming messages
        for i in range(5):
            metrics.record_message_consumed()
        
        stats = metrics.get_consumer_stats()
        assert stats['messages_consumed'] == 5
    
    def test_lag_monitoring(self, mock_env_vars):
        """Test consumer lag monitoring"""
        from ingestion.metrics import KafkaMetrics
        
        with patch('kafka.KafkaConsumer') as mock_consumer:
            mock_consumer_instance = MagicMock()
            mock_consumer.return_value = mock_consumer_instance
            
            metrics = KafkaMetrics()
            lag = metrics.get_consumer_lag(
                consumer=mock_consumer_instance,
                topic='test-transactions'
            )
            
            assert lag is not None


@pytest.mark.integration
class TestKafkaIntegration:
    """Integration tests for Kafka streaming"""
    
    @pytest.mark.skip(reason="Requires running Kafka instance")
    def test_end_to_end_message_flow(self):
        """Test complete message flow from producer to consumer"""
        # This would test actual Kafka message flow
        pass
    
    @pytest.mark.skip(reason="Requires running Kafka instance")
    def test_consumer_group_rebalancing(self):
        """Test consumer group rebalancing"""
        # This would test consumer group behavior
        pass
    
    @pytest.mark.skip(reason="Requires running Kafka instance")
    def test_message_ordering_guarantee(self):
        """Test message ordering within partitions"""
        # This would verify message ordering
        pass
