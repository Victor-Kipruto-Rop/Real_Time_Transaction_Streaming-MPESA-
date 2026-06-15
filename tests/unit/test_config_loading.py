import os
from app.config import settings


def test_settings():
    print("Testing Configuration Loading:")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")
    print(f"KAFKA_BROKERS: {settings.KAFKA_BROKERS}")
    print(f"GRAFANA_URL: {settings.GRAFANA_URL}")
    print(f"UI_TOKEN: {settings.UI_TOKEN}")

    assert settings.POSTGRES_HOST == "localhost"
    assert settings.KAFKA_BROKERS == "localhost:9092"
    assert settings.UI_TOKEN == "your_secure_token_here"
    print("Settings test passed!")


if __name__ == "__main__":
    test_settings()
