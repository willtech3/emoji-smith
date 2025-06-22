"""Tests for webhook security domain service."""

import pytest
from unittest.mock import Mock
from emojismith.domain.services.webhook_security_service import WebhookSecurityService
from emojismith.domain.value_objects.webhook_request import WebhookRequest


@pytest.mark.unit
class TestWebhookSecurityService:
    """Test webhook security domain service."""

    @pytest.fixture
    def mock_signature_validator(self):
        """Mock signature validator."""
        return Mock()

    @pytest.fixture
    def security_service(self, mock_signature_validator):
        """Webhook security service with mocked validator."""
        return WebhookSecurityService(mock_signature_validator)

    def test_validates_authentic_webhook_request(
        self, security_service, mock_signature_validator
    ):
        """Test that authentic webhook requests pass validation."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "message_action"}',
            timestamp="1234567890",
            signature="v0=valid_signature",
        )
        mock_signature_validator.validate_signature.return_value = True

        # Act
        result = security_service.is_authentic_webhook(request)

        # Assert
        assert result is True
        mock_signature_validator.validate_signature.assert_called_once_with(request)

    def test_rejects_inauthentic_webhook_request(
        self, security_service, mock_signature_validator
    ):
        """Test that inauthentic webhook requests are rejected."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "message_action"}',
            timestamp="1234567890",
            signature="v0=invalid_signature",
        )
        mock_signature_validator.validate_signature.return_value = False

        # Act
        result = security_service.is_authentic_webhook(request)

        # Assert
        assert result is False
        mock_signature_validator.validate_signature.assert_called_once_with(request)

    def test_handles_malformed_webhook_request_gracefully(
        self, security_service, mock_signature_validator
    ):
        """Test that malformed requests are handled gracefully."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "test"}', timestamp=None, signature=None
        )
        mock_signature_validator.validate_signature.return_value = False

        # Act
        result = security_service.is_authentic_webhook(request)

        # Assert
        assert result is False
        mock_signature_validator.validate_signature.assert_called_once_with(request)

    def test_delegates_validation_to_signature_validator(
        self, security_service, mock_signature_validator
    ):
        """Test that security service delegates to signature validator."""
        # Arrange
        request = WebhookRequest(
            body=b'{"type": "test"}', timestamp="1234567890", signature="v0=signature"
        )

        # Act
        security_service.is_authentic_webhook(request)

        # Assert
        mock_signature_validator.validate_signature.assert_called_once_with(request)
