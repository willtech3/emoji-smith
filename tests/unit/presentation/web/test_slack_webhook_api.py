import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from emojismith.presentation.web.slack_webhook_api import create_webhook_api
from emojismith.application.handlers.slack_webhook_handler import SlackWebhookHandler


@pytest.fixture
def handler() -> SlackWebhookHandler:
    handler = AsyncMock(spec=SlackWebhookHandler)
    handler.health_check.return_value = {"status": "healthy"}
    handler.handle_event.return_value = {"status": "ok"}
    return handler


def test_health_endpoint(handler: SlackWebhookHandler) -> None:
    app = create_webhook_api(handler)
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}
    handler.health_check.assert_called_once()


def test_events_endpoint(handler: SlackWebhookHandler) -> None:
    app = create_webhook_api(handler)
    client = TestClient(app)
    resp = client.post(
        "/slack/events", data="{}", headers={"content-type": "application/json"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    handler.handle_event.assert_awaited_once()
