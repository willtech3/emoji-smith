"""Tests for Slack signature validator infrastructure."""

import pytest
import hmac
import hashlib
import time
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
)
from emojismith.domain.value_objects.webhook_request import WebhookRequest


class TestSlackSignatureValidator:
    """Test Slack signature validator implementation."""

    @pytest.fixture
    def signing_secret(self):
        """Test signing secret."""
        return "test_signing_secret"

    @pytest.fixture
    def validator(self, signing_secret, monkeypatch):
        """Slack signature validator with test signing secret."""
        monkeypatch.setenv("SLACK_SIGNING_SECRET", signing_secret)
        return SlackSignatureValidator()

    def test_validates_authentic_slack_signature(self, validator, signing_secret):
        """Test that valid Slack signatures pass validation."""
        # Arrange
        body = b'{"type": "url_verification", "challenge": "test"}'
        timestamp = str(int(time.time()))

        # Create valid signature
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        signature = (
            "v0="
            + hmac.new(
                signing_secret.encode("utf-8"),
                sig_basestring.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
        )

        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is True

    def test_rejects_invalid_slack_signature(self, validator):
        """Test that invalid signatures are rejected."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "test"}',
            timestamp=str(int(time.time())),
            signature="v0=invalid_signature",
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False

    def test_rejects_missing_timestamp(self, validator):
        """Test that missing timestamp is rejected."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "test"}', timestamp=None, signature="v0=some_signature"
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False

    def test_rejects_missing_signature(self, validator):
        """Test that missing signature is rejected."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "test"}', timestamp=str(int(time.time())), signature=None
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False

    def test_prevents_replay_attacks_with_old_timestamp(self, validator):
        """Test that old timestamps are rejected to prevent replay attacks."""
        # Arrange - timestamp older than 5 minutes
        old_timestamp = str(int(time.time()) - 400)
        request = WebhookRequest(
            body=b'{"type": "test"}',
            timestamp=old_timestamp,
            signature="v0=some_signature",
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False

    def test_handles_missing_signing_secret_gracefully(self, monkeypatch):
        """Test that missing signing secret is handled gracefully."""
        # Arrange
        monkeypatch.delenv("SLACK_SIGNING_SECRET", raising=False)
        validator = SlackSignatureValidator()
        request = WebhookRequest(
            body=b'{"type": "test"}',
            timestamp=str(int(time.time())),
            signature="v0=some_signature",
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False

    def test_handles_invalid_timestamp_format(self, validator):
        """Test that invalid timestamp format is handled gracefully."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "test"}',
            timestamp="invalid_timestamp",
            signature="v0=some_signature",
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False
