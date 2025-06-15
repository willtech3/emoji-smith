"""Tests for webhook request value object."""

import pytest
from emojismith.domain.value_objects.webhook_request import WebhookRequest


class TestWebhookRequest:
    """Test webhook request value object."""

    def test_creates_valid_webhook_request(self):
        """Test creating a valid webhook request."""
        # Arrange & Act
        request = WebhookRequest(
            body=b'{"type": "message_action"}',
            timestamp="1234567890",
            signature="v0=abc123",
        )

        # Assert
        assert request.body == b'{"type": "message_action"}'
        assert request.timestamp == "1234567890"
        assert request.signature == "v0=abc123"
        assert request.timestamp_int == 1234567890

    def test_allows_none_timestamp_and_signature(self):
        """Test that timestamp and signature can be None."""
        # Arrange & Act
        request = WebhookRequest(
            body=b'{"type": "test"}', timestamp=None, signature=None
        )

        # Assert
        assert request.body == b'{"type": "test"}'
        assert request.timestamp is None
        assert request.signature is None
        assert request.timestamp_int is None

    def test_rejects_empty_body(self):
        """Test that empty body raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Webhook request body cannot be empty"):
            WebhookRequest(body=b"", timestamp="1234567890", signature="v0=abc123")

    def test_rejects_invalid_timestamp_format(self):
        """Test that invalid timestamp format raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(
            ValueError, match="Webhook timestamp must contain only ASCII digits"
        ):
            WebhookRequest(
                body=b'{"type": "test"}', timestamp="invalid", signature="v0=abc123"
            )

    def test_rejects_non_string_timestamp(self):
        """Test that non-string timestamp raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Webhook timestamp must be a string"):
            WebhookRequest(
                body=b'{"type": "test"}', timestamp=1234567890, signature="v0=abc123"
            )

    def test_rejects_empty_signature(self):
        """Test that empty signature raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Webhook signature cannot be empty"):
            WebhookRequest(
                body=b'{"type": "test"}', timestamp="1234567890", signature=""
            )

    def test_rejects_non_string_signature(self):
        """Test that non-string signature raises ValueError."""
        # Arrange & Act & Assert
        with pytest.raises(ValueError, match="Webhook signature must be a string"):
            WebhookRequest(
                body=b'{"type": "test"}', timestamp="1234567890", signature=123
            )

    def test_timestamp_int_property(self):
        """Test that timestamp_int property returns parsed timestamp."""
        # Arrange & Act
        request = WebhookRequest(
            body=b'{"type": "test"}', timestamp="1234567890", signature="v0=abc123"
        )

        # Assert
        assert request.timestamp_int == 1234567890

    def test_webhook_request_is_immutable(self):
        """Test that webhook request is immutable."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "test"}', timestamp="1234567890", signature="v0=abc123"
        )

        # Act & Assert
        with pytest.raises(AttributeError):
            request.body = b'{"type": "modified"}'
