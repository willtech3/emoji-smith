"""Tests for Slack signature validator infrastructure."""

import pytest
import hmac
import hashlib
import time
from unittest.mock import patch
from emojismith.infrastructure.security.slack_signature_validator import (
    SlackSignatureValidator,
    MissingSigningSecretError,
)
from emojismith.domain.value_objects.webhook_request import WebhookRequest


class TestSlackSignatureValidator:
    """Test Slack signature validator implementation."""

    @pytest.fixture
    def signing_secret(self):
        """Test signing secret."""
        return "test_signing_secret"

    @pytest.fixture
    def validator(self, signing_secret):
        """Slack signature validator with test signing secret."""
        return SlackSignatureValidator(signing_secret=signing_secret)

    @pytest.fixture
    def relaxed_validator(self, signing_secret):
        """Validator with extended replay window for deterministic payload tests."""
        return SlackSignatureValidator(
            signing_secret=signing_secret, replay_window_seconds=999999999
        )

    def test_validates_authentic_slack_signature(self, validator, signing_secret):
        """Test that valid Slack signatures pass validation."""
        # Arrange
        body = b'{"type": "url_verification", "challenge": "test"}'
        timestamp = str(int(time.time()))

        # Create valid signature using raw bytes (not decoded)
        sig_basestring = b"v0:" + timestamp.encode() + b":" + body
        signature = (
            "v0="
            + hmac.new(
                signing_secret.encode("utf-8"),
                sig_basestring,
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
        # Arrange - timestamp older than replay window
        replay_window = validator._replay_window
        old_timestamp = str(int(time.time()) - replay_window - 100)
        request = WebhookRequest(
            body=b'{"type": "test"}',
            timestamp=old_timestamp,
            signature="v0=some_signature",
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False

    @patch.dict("os.environ", {}, clear=True)
    def test_handles_missing_signing_secret_raises_error(self):
        """Test that missing signing secret raises MissingSigningSecretError."""
        # Arrange
        validator = SlackSignatureValidator(signing_secret=None)
        request = WebhookRequest(
            body=b'{"type": "test"}',
            timestamp=str(int(time.time())),
            signature="v0=some_signature",
        )

        # Act & Assert
        with pytest.raises(
            MissingSigningSecretError, match="Slack signing secret not configured"
        ):
            validator.validate_signature(request)

    def test_configurable_replay_window(self, signing_secret):
        """Test that replay window is configurable."""
        # Arrange
        custom_window = 600  # 10 minutes
        validator = SlackSignatureValidator(
            signing_secret=signing_secret, replay_window_seconds=custom_window
        )

        # Test that the custom window is set
        assert validator._replay_window == custom_window

        # Test with timestamp just outside custom window
        old_timestamp = str(int(time.time()) - custom_window - 100)
        request = WebhookRequest(
            body=b'{"type": "test"}',
            timestamp=old_timestamp,
            signature="v0=some_signature",
        )

        # Act
        result = validator.validate_signature(request)

        # Assert
        assert result is False

    def test_handles_invalid_timestamp_format_in_webhook_request(self, validator):
        """Test invalid timestamp format is handled via WebhookRequest validation."""
        # Arrange & Act & Assert
        with pytest.raises(
            ValueError, match="Webhook timestamp must contain only ASCII digits"
        ):
            WebhookRequest(
                body=b'{"type": "test"}',
                timestamp="invalid_timestamp",
                signature="v0=some_signature",
            )

    @pytest.fixture
    def known_valid_payload(self, signing_secret):
        """Provide a tuple of body, timestamp and signature for deterministic tests."""
        body = b'{"type":"challenge"}'
        timestamp = "1609459200"  # 2021-01-01T00:00:00Z
        sig_basestring = b"v0:" + timestamp.encode() + b":" + body
        signature = (
            "v0="
            + hmac.new(
                signing_secret.encode("utf-8"), sig_basestring, hashlib.sha256
            ).hexdigest()
        )
        return body, timestamp, signature

    def test_compute_expected_signature_known_value(
        self, relaxed_validator, known_valid_payload
    ):
        """_compute_expected_signature should produce expected HMAC digest."""
        body, timestamp, signature = known_valid_payload
        sig_basestring = b"v0:" + timestamp.encode() + b":" + body

        assert (
            relaxed_validator._compute_expected_signature(sig_basestring) == signature
        )

    def test_validate_signature_accepts_known_payload(
        self, relaxed_validator, known_valid_payload
    ):
        """Validator should accept a correctly signed request."""
        body, timestamp, signature = known_valid_payload
        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)

        assert relaxed_validator.validate_signature(request) is True

    def test_validate_signature_rejects_tampered_body(
        self, relaxed_validator, known_valid_payload
    ):
        """Validator should reject if the body differs from signature."""
        body, timestamp, signature = known_valid_payload
        tampered_body = b'{"type":"changed"}'
        request = WebhookRequest(
            body=tampered_body, timestamp=timestamp, signature=signature
        )

        assert relaxed_validator.validate_signature(request) is False

    def test_validate_signature_rejects_wrong_timestamp(
        self, relaxed_validator, known_valid_payload
    ):
        """Validator should reject if the timestamp differs from signature."""
        body, _timestamp, signature = known_valid_payload
        wrong_timestamp = "1609459201"
        request = WebhookRequest(
            body=body, timestamp=wrong_timestamp, signature=signature
        )

        assert relaxed_validator.validate_signature(request) is False
