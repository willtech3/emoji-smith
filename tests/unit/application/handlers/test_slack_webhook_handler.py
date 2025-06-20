import pytest
from unittest.mock import AsyncMock, Mock

from emojismith.application.handlers.slack_webhook_handler import (
    SlackEventProcessor,
    SlackWebhookHandler,
    UnauthorizedError,
)
from webhook.handler import WebhookHandler
from webhook.security.webhook_security_service import WebhookSecurityService
from webhook.domain.webhook_request import WebhookRequest


class TestSlackWebhookHandler:
    @pytest.fixture
    def security_service(self) -> WebhookSecurityService:
        svc = Mock(spec=WebhookSecurityService)
        svc.is_authentic_webhook = Mock(return_value=True)
        svc.validate_url_verification = Mock(return_value=None)
        return svc

    @pytest.fixture
    def event_processor(self) -> SlackEventProcessor:
        handler = AsyncMock(spec=WebhookHandler)
        processor = SlackEventProcessor(handler)
        processor.process = AsyncMock(return_value={"status": "ok"})
        return processor

    @pytest.fixture
    def webhook_handler(
        self,
        security_service: WebhookSecurityService,
        event_processor: SlackEventProcessor,
    ) -> SlackWebhookHandler:
        return SlackWebhookHandler(security_service, event_processor)

    @pytest.mark.asyncio
    async def test_handles_event_after_validation(
        self,
        webhook_handler: SlackWebhookHandler,
        security_service: WebhookSecurityService,
        event_processor: SlackEventProcessor,
    ) -> None:
        body = b'{"type": "message_action"}'
        headers = {
            "X-Slack-Request-Timestamp": "1",
            "X-Slack-Signature": "sig",
            "content-type": "application/json",
        }
        result = await webhook_handler.handle_event(body, headers)
        assert result == {"status": "ok"}
        security_service.is_authentic_webhook.assert_called()
        event_processor.process.assert_awaited_once_with({"type": "message_action"})

    @pytest.mark.asyncio
    async def test_unauthorized_raises_error(
        self,
        webhook_handler: SlackWebhookHandler,
        security_service: WebhookSecurityService,
    ) -> None:
        security_service.is_authentic_webhook.return_value = False
        body = b"{}"
        headers = {"X-Slack-Request-Timestamp": "1", "X-Slack-Signature": "sig"}
        with pytest.raises(UnauthorizedError):
            await webhook_handler.handle_event(body, headers)
