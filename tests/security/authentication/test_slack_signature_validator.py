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


@pytest.mark.security
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
    def known_signature(self) -> dict[str, str | bytes]:
        """Provide known Slack signature example from documentation."""
        secret = "8f742231b10e8888abcd99yyyzzz85a5"
        timestamp = "1531420618"
        body = b"foo=bar"
        sig_basestring = b"v0:" + timestamp.encode() + b":" + body
        signature = (
            "v0="
            + hmac.new(
                secret.encode("utf-8"), sig_basestring, hashlib.sha256
            ).hexdigest()
        )
        return {
            "secret": secret,
            "timestamp": timestamp,
            "body": body,
            "basestring": sig_basestring,
            "signature": signature,
        }

    def test_validate_with_known_signature_example(self, known_signature):
        """Validator validates correctly with known signature example."""
        validator = SlackSignatureValidator(signing_secret=known_signature["secret"])
        # Test that the validator correctly validates the known signature
        request = WebhookRequest(
            body=known_signature["body"],
            timestamp=known_signature["timestamp"],
            signature=known_signature["signature"],
        )
        with patch(
            "emojismith.infrastructure.security.slack_signature_validator.time.time",
            return_value=int(known_signature["timestamp"]) + 1,
        ):
            assert validator.validate_signature(request) is True

    def test_known_signature_validates(self, known_signature):
        """Validator accepts a genuine Slack signature."""
        validator = SlackSignatureValidator(signing_secret=known_signature["secret"])
        request = WebhookRequest(
            body=known_signature["body"],
            timestamp=known_signature["timestamp"],
            signature=known_signature["signature"],
        )
        with patch(
            "emojismith.infrastructure.security.slack_signature_validator.time.time",
            return_value=int(known_signature["timestamp"]) + 1,
        ):
            assert validator.validate_signature(request) is True

    def test_tampered_body_rejected(self, known_signature):
        """Validator rejects requests with tampered body."""
        validator = SlackSignatureValidator(signing_secret=known_signature["secret"])
        tampered_body = known_signature["body"] + b"tamper"
        request = WebhookRequest(
            body=tampered_body,
            timestamp=known_signature["timestamp"],
            signature=known_signature["signature"],
        )
        with patch(
            "emojismith.infrastructure.security.slack_signature_validator.time.time",
            return_value=int(known_signature["timestamp"]) + 1,
        ):
            assert validator.validate_signature(request) is False

    def test_wrong_timestamp_rejected(self, known_signature):
        """Validator rejects requests signed with a different timestamp."""
        validator = SlackSignatureValidator(signing_secret=known_signature["secret"])
        wrong_timestamp = str(int(known_signature["timestamp"]) + 5)
        request = WebhookRequest(
            body=known_signature["body"],
            timestamp=wrong_timestamp,
            signature=known_signature["signature"],
        )
        with patch(
            "emojismith.infrastructure.security.slack_signature_validator.time.time",
            return_value=int(known_signature["timestamp"]) + 1,
        ):
            assert validator.validate_signature(request) is False
