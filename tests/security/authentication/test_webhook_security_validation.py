"""Unit tests for WebhookSecurityService."""

import json
from unittest.mock import Mock, patch
import pytest

from webhook.domain.webhook_request import WebhookRequest
from webhook.security.webhook_security_service import WebhookSecurityService
from webhook.infrastructure.slack_signature_validator import (
    SlackSignatureValidator,
    MissingSigningSecretError,
)


@pytest.mark.security
class TestWebhookSecurityService:
    """Test cases for WebhookSecurityService."""

    @pytest.fixture
    def mock_signature_validator(self):
        """Fixture providing a mock signature validator."""
        return Mock(spec=SlackSignatureValidator)

    @pytest.fixture
    def security_service(self, mock_signature_validator):
        """Fixture providing a configured security service."""
        return WebhookSecurityService(signature_validator=mock_signature_validator)

    @pytest.fixture
    def valid_webhook_request(self):
        """Fixture providing a valid webhook request."""
        return WebhookRequest(
            body=b'{"type": "event_callback", "event": {"type": "message"}}',
            timestamp="1234567890",
            signature="v0=abc123def456",
        )

    def test_init_with_signature_validator(self, mock_signature_validator):
        """Test initialization with signature validator."""
        service = WebhookSecurityService(signature_validator=mock_signature_validator)
        assert service._signature_validator == mock_signature_validator

    def test_is_authentic_webhook_with_valid_request_returns_true(
        self, security_service, mock_signature_validator, valid_webhook_request
    ):
        """Test that valid webhook request returns True."""
        mock_signature_validator.validate_request.return_value = True

        result = security_service.is_authentic_webhook(valid_webhook_request)

        assert result is True
        mock_signature_validator.validate_request.assert_called_once_with(
            valid_webhook_request
        )

    def test_is_authentic_webhook_with_invalid_signature_returns_false(
        self, security_service, mock_signature_validator, valid_webhook_request
    ):
        """Test that invalid signature returns False."""
        mock_signature_validator.validate_request.return_value = False

        result = security_service.is_authentic_webhook(valid_webhook_request)

        assert result is False
        mock_signature_validator.validate_request.assert_called_once_with(
            valid_webhook_request
        )

    def test_is_authentic_webhook_with_null_request_returns_false(
        self, security_service
    ):
        """Test that null request returns False."""
        result = security_service.is_authentic_webhook(None)
        assert result is False

    def test_is_authentic_webhook_with_missing_body_returns_false(
        self, security_service
    ):
        """Test that request with missing body returns False."""
        request = WebhookRequest(
            body=None, timestamp="1234567890", signature="v0=abc123def456"
        )

        result = security_service.is_authentic_webhook(request)
        assert result is False

    def test_is_authentic_webhook_with_empty_body_returns_false(self, security_service):
        """Test that request with empty body returns False."""
        request = WebhookRequest(
            body=b"", timestamp="1234567890", signature="v0=abc123def456"
        )

        result = security_service.is_authentic_webhook(request)
        assert result is False

    def test_is_authentic_webhook_with_missing_timestamp_returns_false(
        self, security_service
    ):
        """Test that request with missing timestamp returns False."""
        request = WebhookRequest(
            body=b'{"test": "data"}', timestamp=None, signature="v0=abc123def456"
        )

        result = security_service.is_authentic_webhook(request)
        assert result is False

    def test_is_authentic_webhook_with_empty_timestamp_returns_false(
        self, security_service
    ):
        """Test that request with empty timestamp returns False."""
        request = WebhookRequest(
            body=b'{"test": "data"}', timestamp="", signature="v0=abc123def456"
        )

        result = security_service.is_authentic_webhook(request)
        assert result is False

    def test_is_authentic_webhook_with_missing_signature_returns_false(
        self, security_service
    ):
        """Test that request with missing signature returns False."""
        request = WebhookRequest(
            body=b'{"test": "data"}', timestamp="1234567890", signature=None
        )

        result = security_service.is_authentic_webhook(request)
        assert result is False

    def test_is_authentic_webhook_with_empty_signature_returns_false(
        self, security_service
    ):
        """Test that request with empty signature returns False."""
        request = WebhookRequest(
            body=b'{"test": "data"}', timestamp="1234567890", signature=""
        )

        result = security_service.is_authentic_webhook(request)
        assert result is False

    def test_is_authentic_webhook_handles_missing_signing_secret_error(
        self, security_service, mock_signature_validator, valid_webhook_request
    ):
        """Test that MissingSigningSecretError is handled gracefully."""
        mock_signature_validator.validate_request.side_effect = (
            MissingSigningSecretError("Missing secret")
        )

        result = security_service.is_authentic_webhook(valid_webhook_request)

        assert result is False

    def test_is_authentic_webhook_handles_unexpected_errors(
        self, security_service, mock_signature_validator, valid_webhook_request
    ):
        """Test that unexpected errors are handled gracefully."""
        mock_signature_validator.validate_request.side_effect = RuntimeError(
            "Unexpected error"
        )

        result = security_service.is_authentic_webhook(valid_webhook_request)

        assert result is False

    def test_is_authentic_webhook_logs_successful_validation(
        self, security_service, mock_signature_validator, valid_webhook_request, caplog
    ):
        """Test that successful validation is logged."""
        mock_signature_validator.validate_request.return_value = True

        with caplog.at_level("DEBUG"):
            security_service.is_authentic_webhook(valid_webhook_request)

        assert "Webhook signature validation successful" in caplog.text

    def test_is_authentic_webhook_logs_failed_validation(
        self, security_service, mock_signature_validator, valid_webhook_request, caplog
    ):
        """Test that failed validation is logged with context."""
        mock_signature_validator.validate_request.return_value = False

        security_service.is_authentic_webhook(valid_webhook_request)

        assert "Webhook signature validation failed" in caplog.text

    def test_is_authentic_webhook_logs_missing_headers(self, security_service, caplog):
        """Test that missing headers are logged appropriately."""
        request = WebhookRequest(
            body=b'{"test": "data"}', timestamp=None, signature=None
        )

        security_service.is_authentic_webhook(request)

        assert "missing required security headers" in caplog.text

    def test_is_authentic_webhook_logs_null_request(self, security_service, caplog):
        """Test that null request is logged."""
        security_service.is_authentic_webhook(None)
        assert "Received null webhook request" in caplog.text

    def test_is_authentic_webhook_logs_missing_body(self, security_service, caplog):
        """Test that missing body is logged."""
        request = WebhookRequest(
            body=None, timestamp="1234567890", signature="v0=abc123def456"
        )

        security_service.is_authentic_webhook(request)
        assert "Webhook request missing body" in caplog.text

    def test_is_authentic_webhook_logs_missing_signing_secret(
        self, security_service, mock_signature_validator, valid_webhook_request, caplog
    ):
        """Test that missing signing secret error is logged."""
        mock_signature_validator.validate_request.side_effect = (
            MissingSigningSecretError("Missing secret")
        )

        security_service.is_authentic_webhook(valid_webhook_request)

        assert "Missing signing secret" in caplog.text

    def test_is_authentic_webhook_logs_unexpected_error(
        self, security_service, mock_signature_validator, valid_webhook_request, caplog
    ):
        """Test that unexpected errors are logged with details."""
        error_message = "Unexpected validation error"
        mock_signature_validator.validate_request.side_effect = RuntimeError(
            error_message
        )

        security_service.is_authentic_webhook(valid_webhook_request)

        assert "Unexpected error during webhook validation" in caplog.text

    def test_validate_url_verification_with_valid_challenge_returns_challenge(
        self, security_service
    ):
        """Test that valid URL verification returns challenge."""
        challenge = "test_challenge_12345"
        payload = {"type": "url_verification", "challenge": challenge}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        result = security_service.validate_url_verification(request)

        assert result == challenge

    def test_validate_url_verification_with_missing_challenge_returns_none(
        self, security_service
    ):
        """Test that URL verification without challenge returns None."""
        payload = {"type": "url_verification"}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        result = security_service.validate_url_verification(request)

        assert result is None

    def test_validate_url_verification_with_non_verification_type_returns_none(
        self, security_service
    ):
        """Test that non-URL verification request returns None."""
        payload = {"type": "event_callback", "event": {"type": "message"}}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        result = security_service.validate_url_verification(request)

        assert result is None

    def test_validate_url_verification_with_null_request_returns_none(
        self, security_service
    ):
        """Test that null request returns None."""
        result = security_service.validate_url_verification(None)
        assert result is None

    def test_validate_url_verification_with_missing_body_returns_none(
        self, security_service
    ):
        """Test that request without body returns None."""
        request = WebhookRequest(body=None, timestamp=None, signature=None)
        result = security_service.validate_url_verification(request)
        assert result is None

    def test_validate_url_verification_with_invalid_json_returns_none(
        self, security_service
    ):
        """Test that invalid JSON returns None."""
        request = WebhookRequest(
            body=b"invalid json content", timestamp=None, signature=None
        )

        result = security_service.validate_url_verification(request)
        assert result is None

    def test_validate_url_verification_with_invalid_utf8_returns_none(
        self, security_service
    ):
        """Test that invalid UTF-8 encoding returns None."""
        request = WebhookRequest(
            body=b"\xff\xfe invalid utf-8", timestamp=None, signature=None
        )

        result = security_service.validate_url_verification(request)
        assert result is None

    def test_validate_url_verification_logs_successful_challenge(
        self, security_service, caplog
    ):
        """Test that successful URL verification is logged."""
        challenge = "test_challenge_12345"
        payload = {"type": "url_verification", "challenge": challenge}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        with caplog.at_level("INFO"):
            security_service.validate_url_verification(request)

        assert "Handling Slack URL verification challenge" in caplog.text

    def test_validate_url_verification_logs_missing_challenge(
        self, security_service, caplog
    ):
        """Test that missing challenge is logged."""
        payload = {"type": "url_verification"}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        security_service.validate_url_verification(request)

        assert "URL verification request missing challenge" in caplog.text

    def test_validate_url_verification_logs_json_decode_error(
        self, security_service, caplog
    ):
        """Test that JSON decode errors are logged at debug level."""
        request = WebhookRequest(body=b"invalid json", timestamp=None, signature=None)

        with caplog.at_level("DEBUG"):
            security_service.validate_url_verification(request)

        assert "Request body is not valid JSON" in caplog.text

    def test_validate_url_verification_handles_unexpected_errors(
        self, security_service
    ):
        """Test that unexpected errors during URL verification are handled."""
        request = WebhookRequest(
            body=b'{"type": "url_verification", "challenge": "test"}',
            timestamp=None,
            signature=None,
        )

        # Mock json.loads to raise an unexpected error
        with patch("json.loads", side_effect=RuntimeError("Unexpected error")):
            result = security_service.validate_url_verification(request)
            assert result is None

    def test_should_skip_validation_returns_true_for_url_verification(
        self, security_service
    ):
        """Test that should_skip_validation returns True for URL verification."""
        challenge = "test_challenge_12345"
        payload = {"type": "url_verification", "challenge": challenge}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        result = security_service.should_skip_validation(request)

        assert result is True

    def test_should_skip_validation_returns_false_for_regular_webhook(
        self, security_service
    ):
        """Test that should_skip_validation returns False for regular webhooks."""
        payload = {"type": "event_callback", "event": {"type": "message"}}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp="123", signature="v0=abc")
        result = security_service.should_skip_validation(request)

        assert result is False

    def test_validate_url_verification_with_empty_challenge_returns_none(
        self, security_service
    ):
        """Test that empty challenge returns None."""
        payload = {"type": "url_verification", "challenge": ""}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        result = security_service.validate_url_verification(request)

        assert result is None

    def test_validate_url_verification_with_non_string_challenge_works(
        self, security_service
    ):
        """Test that non-string challenge (like number) is handled."""
        payload = {"type": "url_verification", "challenge": 12345}
        body = json.dumps(payload).encode("utf-8")

        request = WebhookRequest(body=body, timestamp=None, signature=None)
        result = security_service.validate_url_verification(request)

        assert result == "12345"

    def test_comprehensive_webhook_flow_with_valid_request(
        self, security_service, mock_signature_validator
    ):
        """Test comprehensive flow with valid webhook request."""
        # Setup valid request
        request = WebhookRequest(
            body=b'{"type": "event_callback", "event": {"type": "message", '
            b'"text": "hello"}}',
            timestamp="1234567890",
            signature="v0=valid_signature",
        )

        # Configure validator to return True
        mock_signature_validator.validate_request.return_value = True

        # Should not skip validation
        assert security_service.should_skip_validation(request) is False

        # Should authenticate successfully
        assert security_service.is_authentic_webhook(request) is True

        # Should not be URL verification
        assert security_service.validate_url_verification(request) is None

    def test_comprehensive_webhook_flow_with_url_verification(self, security_service):
        """Test comprehensive flow with URL verification request."""
        # Setup URL verification request
        challenge = "verification_challenge_12345"
        payload = {"type": "url_verification", "challenge": challenge}
        request = WebhookRequest(
            body=json.dumps(payload).encode("utf-8"), timestamp=None, signature=None
        )

        # Should skip validation
        assert security_service.should_skip_validation(request) is True

        # Should return challenge
        assert security_service.validate_url_verification(request) == challenge

        # Authentication should still work (though not needed for URL verification)
        assert (
            security_service.is_authentic_webhook(request) is False
        )  # Missing headers
