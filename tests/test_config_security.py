"""Regression tests for security-sensitive configuration parsing."""

import pytest
from pydantic import ValidationError

from app.config import Settings


def test_signature_enforcement_is_not_silently_disabled_without_secret():
    settings = Settings(WEBHOOK_SIGNING_SECRET="", REQUIRE_WEBHOOK_SIGNATURE=True)

    assert settings.REQUIRE_WEBHOOK_SIGNATURE is True
    assert settings.WEBHOOK_SIGNING_SECRET == ""


@pytest.mark.parametrize("value", ["maybe", "sometimes", "enabled-ish"])
def test_invalid_signature_enforcement_values_are_rejected(value):
    with pytest.raises(ValidationError):
        Settings(REQUIRE_WEBHOOK_SIGNATURE=value)


@pytest.mark.parametrize("value", ["1", "true", "YES", "on"])
def test_truthy_signature_enforcement_values_are_accepted(value):
    settings = Settings(REQUIRE_WEBHOOK_SIGNATURE=value)

    assert settings.REQUIRE_WEBHOOK_SIGNATURE is True


@pytest.mark.parametrize("value", ["0", "false", "NO", "off", ""])
def test_false_signature_enforcement_values_are_accepted(value):
    settings = Settings(REQUIRE_WEBHOOK_SIGNATURE=value)

    assert settings.REQUIRE_WEBHOOK_SIGNATURE is False


def test_placeholder_secret_is_rejected():
    with pytest.raises(ValidationError):
        Settings(SECRET_KEY="change_me")
