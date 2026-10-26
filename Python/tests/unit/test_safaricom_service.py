import pytest
from app.services.safaricom import SafaricomService


def test_safaricom_service_init():
    service = SafaricomService()
    assert service is not None
