"""Tests for SlackWebhookHandler application logic."""

import json
import pytest
from unittest.mock import AsyncMock, Mock

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    UnauthorizedError,
)
from webhook.handler import WebhookHandler
from webhook.security.webhook_security_service import WebhookSecurityService


class TestSlackWebhookHandler:
    @pytest.fixture
    def mock_security_service(self) -> WebhookSecurityService:
        svc = Mock(spec=WebhookSecurityService)
        svc.is_authentic_webhook.return_value = True
        return svc

    @pytest.fixture
    def mock_event_processor(self) -> WebhookHandler:
        return AsyncMock(spec=WebhookHandler)

    @pytest.fixture
    def handler(
        self, mock_security_service, mock_event_processor
    ) -> SlackWebhookHandler:
        return SlackWebhookHandler(mock_security_service, mock_event_processor)

    async def test_processes_message_action_event(
        self, handler: SlackWebhookHandler, mock_event_processor: AsyncMock
    ) -> None:
        body = json.dumps({"type": "message_action"}).encode()
        headers = {
            "content-type": "application/json",
            "X-Slack-Request-Timestamp": "1",
            "X-Slack-Signature": "sig",
        }

        mock_event_processor.handle_message_action.return_value = {"status": "ok"}

        result = await handler.handle_event(body, headers)

        assert result == {"status": "ok"}
        mock_event_processor.handle_message_action.assert_called_once()

    async def test_invalid_signature_raises_error(
        self, mock_security_service: Mock, handler: SlackWebhookHandler
    ) -> None:
        mock_security_service.is_authentic_webhook.return_value = False
        body = b"{}"
        headers = {
            "content-type": "application/json",
            "X-Slack-Request-Timestamp": "1",
            "X-Slack-Signature": "sig",
        }

        with pytest.raises(UnauthorizedError):
            await handler.handle_event(body, headers)

    async def test_url_verification_bypasses_auth(
        self, mock_security_service: Mock, handler: SlackWebhookHandler
    ) -> None:
        body = json.dumps({"type": "url_verification", "challenge": "abc"}).encode()
        headers = {
            "content-type": "application/json",
            "X-Slack-Request-Timestamp": "1",
            "X-Slack-Signature": "sig",
        }

        result = await handler.handle_event(body, headers)

        assert result == {"challenge": "abc"}
        mock_security_service.is_authentic_webhook.assert_not_called()
