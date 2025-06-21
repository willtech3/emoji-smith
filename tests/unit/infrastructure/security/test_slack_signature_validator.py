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
    def known_signature_data(self, signing_secret):
        """Provide known data with precomputed signature."""
        body = b'{"emoji": ":wave:"}'
        timestamp = str(int(time.time()))
        sig_basestring = b"v0:" + timestamp.encode() + b":" + body
        signature = (
            "v0="
            + hmac.new(
                signing_secret.encode("utf-8"),
                sig_basestring,
                hashlib.sha256,
            ).hexdigest()
        )
        return body, timestamp, sig_basestring, signature

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

    def test_expected_signature_matches_fixture(self, validator, known_signature_data):
        """Validator produces expected signature for known base string."""
        _, _, sig_basestring, expected_signature = known_signature_data
        assert (
            validator._compute_expected_signature(sig_basestring) == expected_signature
        )

    def test_valid_signature_from_fixture(self, validator, known_signature_data):
        """Validator accepts known authentic request."""
        body, timestamp, _, signature = known_signature_data
        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)
        assert validator.validate_signature(request) is True

    def test_tampered_body_fails(self, validator, known_signature_data):
        """Validator rejects when body is modified."""
        body, timestamp, _, signature = known_signature_data
        request = WebhookRequest(
            body=b"tampered", timestamp=timestamp, signature=signature
        )
        assert validator.validate_signature(request) is False

    def test_wrong_timestamp_fails(self, validator, known_signature_data):
        """Validator rejects when timestamp does not match signature."""
        body, timestamp, _, signature = known_signature_data
        wrong_timestamp = str(int(timestamp) + 1)
        request = WebhookRequest(
            body=body, timestamp=wrong_timestamp, signature=signature
        )
        assert validator.validate_signature(request) is False
