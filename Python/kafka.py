"""Lightweight kafka-python compatibility shim for tests."""


class KafkaProducer:
    def __init__(self, *args, **kwargs):
        pass

    def send(self, *args, **kwargs):
        return None

    def flush(self, *args, **kwargs):
        return None

    def close(self, *args, **kwargs):
        return None


class KafkaConsumer:
    def __init__(self, *args, **kwargs):
        self._messages = []

    def __iter__(self):
        return iter(self._messages)

    def commit(self, *args, **kwargs):
        return None

    def close(self, *args, **kwargs):
        return None
