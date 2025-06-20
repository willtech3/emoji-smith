import pytest
from unittest.mock import AsyncMock, MagicMock

from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    UnauthorizedError,
)
from emojismith.domain.services.webhook_security_service import WebhookSecurityService


@pytest.fixture
def mock_security_service() -> MagicMock:
    return MagicMock(spec=WebhookSecurityService)


@pytest.fixture
def mock_event_processor() -> AsyncMock:
    processor = AsyncMock()
    processor.process = AsyncMock(return_value={"ok": True})
    return processor


@pytest.fixture
def handler(
    mock_security_service: MagicMock, mock_event_processor: AsyncMock
) -> SlackWebhookHandler:
    return SlackWebhookHandler(mock_security_service, mock_event_processor)


@pytest.mark.asyncio
async def test_handle_event_calls_processor_when_authorized(
    handler: SlackWebhookHandler,
    mock_security_service: MagicMock,
    mock_event_processor: AsyncMock,
) -> None:
    mock_security_service.is_authentic_webhook.return_value = True

    result = await handler.handle_event(
        b"{}", {"X-Slack-Request-Timestamp": "1", "X-Slack-Signature": "sig"}
    )

    assert result == {"ok": True}
    mock_event_processor.process.assert_awaited_once_with(b"{}")


@pytest.mark.asyncio
async def test_handle_event_raises_when_unauthorized(
    handler: SlackWebhookHandler,
    mock_security_service: MagicMock,
    mock_event_processor: AsyncMock,
) -> None:
    mock_security_service.is_authentic_webhook.return_value = False

    with pytest.raises(UnauthorizedError):
        await handler.handle_event(
            b"{}", {"X-Slack-Request-Timestamp": "1", "X-Slack-Signature": "sig"}
        )

    mock_event_processor.process.assert_not_called()
