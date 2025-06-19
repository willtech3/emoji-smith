"""Unit tests for SlackSignatureValidator."""

import time
from unittest.mock import patch
import pytest

from webhook.domain.webhook_request import WebhookRequest
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator


class TestSlackSignatureValidator:
    """Test cases for SlackSignatureValidator."""

    @pytest.fixture
    def signing_secret_bytes(self):
        """Fixture providing a test signing secret as bytes."""
        return b"test_signing_secret_123"

    @pytest.fixture
    def validator(self, signing_secret_bytes):
        """Fixture providing a configured validator."""
        return SlackSignatureValidator(signing_secret=signing_secret_bytes)

    @pytest.fixture
    def valid_request_data(self):
        """Fixture providing valid request data."""
        body = (
            b'{"type": "event_callback", "event": {"type": "message", "text": "hello"}}'
        )
        timestamp = str(int(time.time()))
        return {"body": body, "timestamp": timestamp}

    def test_init_with_valid_secret(self, signing_secret_bytes):
        """Test initialization with valid signing secret as bytes."""
        validator = SlackSignatureValidator(signing_secret=signing_secret_bytes)
        assert validator._signing_secret == signing_secret_bytes
        assert validator._replay_window == SlackSignatureValidator.DEFAULT_REPLAY_WINDOW

    def test_init_with_custom_replay_window(self, signing_secret_bytes):
        """Test initialization with custom replay window."""
        custom_window = 600
        validator = SlackSignatureValidator(
            signing_secret=signing_secret_bytes,
            replay_window_seconds=custom_window,
        )
        assert validator._replay_window == custom_window

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

    def test_validate_with_none_timestamp_returns_false(self, validator):
        """Test that None timestamp returns False."""
        body = b'{"test": "data"}'
        signature = "v0=some_signature"

        result = validator.validate(body, None, signature)
        assert result is False

    def test_validate_with_missing_signature_returns_false(self, validator):
        """Test that missing signature returns False."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))

        result = validator.validate(body, timestamp, "")
        assert result is False

    def test_validate_with_none_signature_returns_false(self, validator):
        """Test that None signature returns False."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))

        result = validator.validate(body, timestamp, None)
        assert result is False

    def test_validate_with_signature_missing_v0_prefix_returns_false(self, validator):
        """Test that signature without v0= prefix returns False."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))
        signature_without_prefix = "invalid_signature_without_prefix"

        result = validator.validate(body, timestamp, signature_without_prefix)
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

    @patch("webhook.infrastructure.slack_signature_validator.time.time")
    def test_validate_at_replay_window_boundary_returns_false(
        self, mock_time, validator
    ):
        """Test validation at exactly replay window boundary is rejected for security."""
        current_time = 1000000
        mock_time.return_value = current_time

        # Test at boundary (exactly at window limit) - should be rejected
        boundary_timestamp = str(
            current_time - SlackSignatureValidator.DEFAULT_REPLAY_WINDOW
        )
        body = b'{"test": "data"}'

        # Create valid signature for boundary timestamp
        sig_basestring = f"v0:{boundary_timestamp}:".encode() + body
        signature = validator._compute_expected_signature(sig_basestring)

        result = validator.validate(body, boundary_timestamp, signature)
        assert result is False

    @patch("webhook.infrastructure.slack_signature_validator.time.time")
    def test_validate_beyond_replay_window_boundary_returns_false(
        self, mock_time, validator
    ):
        """Test validation beyond replay window boundary is rejected."""
        current_time = 1000000
        mock_time.return_value = current_time

        # Test beyond boundary (exactly at window limit + 1)
        beyond_boundary_timestamp = str(
            current_time - SlackSignatureValidator.DEFAULT_REPLAY_WINDOW - 1
        )
        body = b'{"test": "data"}'

        # Create valid signature for beyond boundary timestamp
        sig_basestring = f"v0:{beyond_boundary_timestamp}:".encode() + body
        signature = validator._compute_expected_signature(sig_basestring)

        result = validator.validate(body, beyond_boundary_timestamp, signature)
        assert result is False

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

        # Test None timestamp
        caplog.clear()
        validator.validate(body, None, "v0=signature")
        assert "Missing timestamp or signature" in caplog.text

        # Test None signature
        caplog.clear()
        validator.validate(body, "1234567890", None)
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

    def test_validate_logs_warning_for_signature_mismatch_with_safe_logging(
        self, validator, caplog
    ):
        """Test that signature validation failure is logged safely without PII."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))
        invalid_signature = "v0=invalid_signature"

        validator.validate(body, timestamp, invalid_signature)
        assert "Webhook signature validation failed" in caplog.text

        # Check log records for structured logging
        failure_records = [
            r for r in caplog.records if "signature validation failed" in r.getMessage()
        ]
        assert len(failure_records) == 1

        log_record = failure_records[0]
        # Should log body hash in extra, not raw body
        assert hasattr(log_record, "body_hash")
        assert hasattr(log_record, "timestamp")
        # Should not log raw body anywhere
        assert '{"test": "data"}' not in caplog.text

    def test_validate_logs_warning_for_missing_v0_prefix(self, validator, caplog):
        """Test that missing v0= prefix is logged."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))
        signature_without_prefix = "invalid_signature_without_prefix"

        validator.validate(body, timestamp, signature_without_prefix)
        assert "Signature does not have required v0= prefix" in caplog.text

    def test_validate_handles_unexpected_errors_gracefully(self, validator):
        """Test that unexpected errors during validation are handled gracefully."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))
        signature = "v0=valid_looking_signature"

        # Mock hmac.compare_digest to raise an exception
        with patch(
            "webhook.infrastructure.slack_signature_validator.hmac.compare_digest",
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

    def test_prefix_stripping_in_comparison(self, validator):
        """Test that v0= prefix is properly stripped before comparison."""
        body = b'{"test": "data"}'
        timestamp = str(int(time.time()))

        # Create valid signature
        sig_basestring = f"v0:{timestamp}:".encode() + body
        expected_signature = validator._compute_expected_signature(sig_basestring)

        # Test with properly formatted signature
        result = validator.validate(body, timestamp, expected_signature)
        assert result is True

        # Test that we can't fool it with double prefix
        double_prefix_signature = "v0=" + expected_signature
        result = validator.validate(body, timestamp, double_prefix_signature)
        assert result is False

    @pytest.mark.parametrize("time_offset", [0, -299, 299])
    def test_replay_window_edge_cases(self, validator, time_offset):
        """Test replay window edge cases using parametrize."""
        with patch(
            "webhook.infrastructure.slack_signature_validator.time.time"
        ) as mock_time:
            current_time = 1000000
            mock_time.return_value = current_time

            timestamp = str(current_time + time_offset)
            body = b'{"test": "data"}'

            # Create valid signature
            sig_basestring = f"v0:{timestamp}:".encode() + body
            signature = validator._compute_expected_signature(sig_basestring)

            result = validator.validate(body, timestamp, signature)
            assert result is True  # All these should be within window

    @pytest.mark.parametrize("time_offset", [-300, 300])
    def test_replay_window_boundary_cases(self, validator, time_offset):
        """Test replay window boundary cases - exactly at boundary should be rejected for security."""
        with patch(
            "webhook.infrastructure.slack_signature_validator.time.time"
        ) as mock_time:
            current_time = 1000000
            mock_time.return_value = current_time

            timestamp = str(current_time + time_offset)
            body = b'{"test": "data"}'

            # Create valid signature
            sig_basestring = f"v0:{timestamp}:".encode() + body
            signature = validator._compute_expected_signature(sig_basestring)

            result = validator.validate(body, timestamp, signature)
            assert (
                result is False
            )  # Exactly at boundary should be rejected for security

    @pytest.mark.parametrize("time_offset", [-301, 301])
    def test_replay_window_outside_boundary_cases(self, validator, time_offset):
        """Test replay window outside boundary cases using parametrize."""
        with patch(
            "webhook.infrastructure.slack_signature_validator.time.time"
        ) as mock_time:
            current_time = 1000000
            mock_time.return_value = current_time

            timestamp = str(current_time + time_offset)
            body = b'{"test": "data"}'

            # Create valid signature
            sig_basestring = f"v0:{timestamp}:".encode() + body
            signature = validator._compute_expected_signature(sig_basestring)

            result = validator.validate(body, timestamp, signature)
            assert result is False  # Outside boundary should be rejected
