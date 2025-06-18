"""Unit tests for SlackSignatureValidator."""

import time
from unittest.mock import patch
import pytest

from webhook.domain.webhook_request import WebhookRequest
from webhook.security.slack_signature_validator import (
    SlackSignatureValidator,
    MissingSigningSecretError,
)


class TestSlackSignatureValidator:
    """Test cases for SlackSignatureValidator."""

    @pytest.fixture
    def signing_secret(self):
        """Fixture providing a test signing secret."""
        return "test_signing_secret_123"

    @pytest.fixture
    def validator(self, signing_secret):
        """Fixture providing a configured validator."""
        return SlackSignatureValidator(signing_secret=signing_secret)

    @pytest.fixture
    def valid_request_data(self):
        """Fixture providing valid request data."""
        body = (
            b'{"type": "event_callback", "event": {"type": "message", "text": "hello"}}'
        )
        timestamp = str(int(time.time()))
        return {"body": body, "timestamp": timestamp}

    def test_init_with_valid_secret(self, signing_secret):
        """Test initialization with valid signing secret."""
        validator = SlackSignatureValidator(signing_secret=signing_secret)
        assert validator._signing_secret == signing_secret.encode()
        assert validator._replay_window == SlackSignatureValidator.DEFAULT_REPLAY_WINDOW

    def test_init_with_custom_replay_window(self, signing_secret):
        """Test initialization with custom replay window."""
        custom_window = 600
        validator = SlackSignatureValidator(
            signing_secret=signing_secret,
            replay_window_seconds=custom_window,
        )
        assert validator._replay_window == custom_window

    def test_init_with_empty_secret_raises_error(self):
        """Test that empty signing secret raises MissingSigningSecretError."""
        with pytest.raises(
            MissingSigningSecretError, match="Slack signing secret is required"
        ):
            SlackSignatureValidator(signing_secret="")

    def test_init_with_none_secret_raises_error(self):
        """Test that None signing secret raises MissingSigningSecretError."""
        with pytest.raises(
            MissingSigningSecretError, match="Slack signing secret is required"
        ):
            SlackSignatureValidator(signing_secret=None)

    def test_validate_with_valid_signature_returns_true(
        self, validator, valid_request_data
    ):
        """Test that valid signature returns True."""
        body = valid_request_data["body"]
        timestamp = valid_request_data["timestamp"]

        # Create valid signature
        sig_basestring = f"v0:{timestamp}:".encode() + body
        expected_signature = validator._compute_expected_signature(sig_basestring)

        result = validator.validate(body, timestamp, expected_signature)
        assert result is True

    def test_validate_with_invalid_signature_returns_false(
        self, validator, valid_request_data
    ):
        """Test that invalid signature returns False."""
        body = valid_request_data["body"]
        timestamp = valid_request_data["timestamp"]
        invalid_signature = "v0=invalid_signature"

        result = validator.validate(body, timestamp, invalid_signature)
        assert result is False

    def test_validate_with_missing_timestamp_returns_false(self, validator):
        """Test that missing timestamp returns False."""
        body = b'{"test": "data"}'
        signature = "v0=some_signature"

        result = validator.validate(body, "", signature)
        assert result is False

    def test_validate_with_missing_signature_returns_false(self, validator):
        """Test that missing signature returns False."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))

        result = validator.validate(body, timestamp, "")
        assert result is False

    def test_validate_with_old_timestamp_returns_false(self, validator):
        """Test that old timestamp outside replay window returns False."""
        body = b'{"test": "data"}'
        old_timestamp = str(
            int(time.time()) - 400
        )  # 400 seconds ago (> 300 default window)
        signature = "v0=some_signature"

        result = validator.validate(body, old_timestamp, signature)
        assert result is False

    def test_validate_with_future_timestamp_returns_false(self, validator):
        """Test that future timestamp outside replay window returns False."""
        body = b'{"test": "data"}'
        future_timestamp = str(int(time.time()) + 400)  # 400 seconds in future
        signature = "v0=some_signature"

        result = validator.validate(body, future_timestamp, signature)
        assert result is False

    def test_validate_with_invalid_timestamp_format_returns_false(self, validator):
        """Test that invalid timestamp format returns False."""
        body = b'{"test": "data"}'
        invalid_timestamp = "not_a_number"
        signature = "v0=some_signature"

        result = validator.validate(body, invalid_timestamp, signature)
        assert result is False

    def test_validate_request_with_valid_request_returns_true(
        self, validator, valid_request_data
    ):
        """Test validate_request with valid WebhookRequest returns True."""
        body = valid_request_data["body"]
        timestamp = valid_request_data["timestamp"]

        # Create valid signature
        sig_basestring = f"v0:{timestamp}:".encode() + body
        signature = validator._compute_expected_signature(sig_basestring)

        request = WebhookRequest(body=body, timestamp=timestamp, signature=signature)
        result = validator.validate_request(request)
        assert result is True

    def test_validate_request_with_missing_timestamp_returns_false(self, validator):
        """Test validate_request with missing timestamp returns False."""
        request = WebhookRequest(
            body=b'{"test": "data"}', timestamp=None, signature="v0=some_signature"
        )

        result = validator.validate_request(request)
        assert result is False

    def test_validate_request_with_missing_signature_returns_false(self, validator):
        """Test validate_request with missing signature returns False."""
        request = WebhookRequest(
            body=b'{"test": "data"}', timestamp=str(int(time.time())), signature=None
        )

        result = validator.validate_request(request)
        assert result is False

    def test_compute_expected_signature_produces_correct_format(self, validator):
        """Test that _compute_expected_signature produces correct format."""
        sig_basestring = b"v0:1234567890:test_body"
        signature = validator._compute_expected_signature(sig_basestring)

        assert signature.startswith("v0=")
        assert len(signature) == 67  # "v0=" + 64 hex chars

    def test_compute_expected_signature_consistent_results(self, validator):
        """Test that _compute_expected_signature produces consistent results."""
        sig_basestring = b"v0:1234567890:test_body"
        signature1 = validator._compute_expected_signature(sig_basestring)
        signature2 = validator._compute_expected_signature(sig_basestring)

        assert signature1 == signature2

    def test_compute_expected_signature_different_inputs_different_outputs(
        self, validator
    ):
        """Test that different inputs produce different signatures."""
        sig_basestring1 = b"v0:1234567890:test_body_1"
        sig_basestring2 = b"v0:1234567890:test_body_2"

        signature1 = validator._compute_expected_signature(sig_basestring1)
        signature2 = validator._compute_expected_signature(sig_basestring2)

        assert signature1 != signature2

    @patch("webhook.security.slack_signature_validator.time.time")
    def test_validate_within_replay_window(self, mock_time, validator):
        """Test validation within replay window boundary."""
        current_time = 1000000
        mock_time.return_value = current_time

        # Test at boundary (exactly at window limit)
        boundary_timestamp = str(
            current_time - SlackSignatureValidator.DEFAULT_REPLAY_WINDOW
        )
        body = b'{"test": "data"}'

        # Create valid signature for boundary timestamp
        sig_basestring = f"v0:{boundary_timestamp}:".encode() + body
        signature = validator._compute_expected_signature(sig_basestring)

        result = validator.validate(body, boundary_timestamp, signature)
        assert result is True

    def test_validate_logs_warning_for_missing_headers(self, validator, caplog):
        """Test that missing headers are logged appropriately."""
        body = b'{"test": "data"}'

        # Test missing timestamp
        validator.validate(body, "", "v0=signature")
        assert "Missing timestamp or signature" in caplog.text

        # Test missing signature
        caplog.clear()
        validator.validate(body, "1234567890", "")
        assert "Missing timestamp or signature" in caplog.text

    def test_validate_logs_warning_for_replay_attack(self, validator, caplog):
        """Test that replay attack attempts are logged."""
        body = b'{"test": "data"}'
        old_timestamp = str(int(time.time()) - 400)
        signature = "v0=some_signature"

        validator.validate(body, old_timestamp, signature)
        assert "timestamp outside replay window" in caplog.text

    def test_validate_logs_warning_for_invalid_timestamp(self, validator, caplog):
        """Test that invalid timestamp format is logged."""
        body = b'{"test": "data"}'
        invalid_timestamp = "not_a_number"
        signature = "v0=some_signature"

        validator.validate(body, invalid_timestamp, signature)
        assert "Invalid timestamp format" in caplog.text

    def test_validate_logs_warning_for_signature_mismatch(self, validator, caplog):
        """Test that signature validation failure is logged."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))
        invalid_signature = "v0=invalid_signature"

        validator.validate(body, timestamp, invalid_signature)
        assert "Webhook signature validation failed" in caplog.text

    def test_validate_handles_unexpected_errors_gracefully(self, validator):
        """Test that unexpected errors during validation are handled gracefully."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))
        signature = "v0=valid_looking_signature"

        # Mock hmac.compare_digest to raise an exception
        with patch(
            "webhook.security.slack_signature_validator.hmac.compare_digest",
            side_effect=RuntimeError("Unexpected error"),
        ):
            result = validator.validate(body, timestamp, signature)
            assert result is False

    def test_edge_case_empty_body(self, validator):
        """Test validation with empty request body."""
        body = b""
        timestamp = str(int(time.time()))

        # Create valid signature for empty body
        sig_basestring = f"v0:{timestamp}:".encode() + body
        signature = validator._compute_expected_signature(sig_basestring)

        result = validator.validate(body, timestamp, signature)
        assert result is True

    def test_edge_case_large_body(self, validator):
        """Test validation with large request body."""
        body = b'{"data": "' + b"x" * 10000 + b'"}'
        timestamp = str(int(time.time()))

        # Create valid signature for large body
        sig_basestring = f"v0:{timestamp}:".encode() + body
        signature = validator._compute_expected_signature(sig_basestring)

        result = validator.validate(body, timestamp, signature)
        assert result is True

    def test_unicode_handling_in_body(self, validator):
        """Test that unicode characters in body are handled correctly."""
        body = '{"message": "Hello 🌟 World"}'.encode("utf-8")
        timestamp = str(int(time.time()))

        # Create valid signature for unicode body
        sig_basestring = f"v0:{timestamp}:".encode() + body
        signature = validator._compute_expected_signature(sig_basestring)

        result = validator.validate(body, timestamp, signature)
        assert result is True
