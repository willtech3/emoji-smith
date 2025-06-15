"""Tests for FastAPI application."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from src.emojismith.app import create_app


class TestFastAPIApp:
    """Test FastAPI application endpoints."""

    @pytest.fixture
    def mock_webhook_handler(self):
        return AsyncMock()

    @pytest.fixture
    def app(self, mock_webhook_handler):
        mock_security_service = AsyncMock()
        with patch(
            "src.emojismith.app.create_webhook_handler",
            return_value=(mock_webhook_handler, mock_security_service),
        ):
            return create_app()

    @pytest.fixture
    def client(self, app):
        return TestClient(app)

    def test_health_check_endpoint(self, client):
        """Test health check endpoint responds correctly."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_processes_slack_emoji_creation_requests(
        self, client, mock_webhook_handler
    ):
        """Test Slack events endpoint accepts POST requests."""
        mock_webhook_handler.handle_message_action.return_value = {"status": "ok"}

        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "123456789.987654321.abcdefghijklmnopqrstuvwxyz",
            "user": {"id": "U12345"},
            "channel": {"id": "C67890"},
            "message": {
                "text": "Test message",
                "ts": "1234567890.123456",
                "user": "U98765",
            },
            "team": {"id": "T11111"},
        }

        response = client.post("/slack/events", json=payload)

        assert response.status_code == 200
        mock_webhook_handler.handle_message_action.assert_called_once_with(payload)

    def test_requires_post_method_for_slack_events(self, client):
        """Test Slack events endpoint rejects GET requests."""
        response = client.get("/slack/events")

        assert response.status_code == 405  # Method Not Allowed

    def test_slack_events_url_verification(self, client):
        """Test Slack URL verification challenge is echoed back."""
        payload = {"type": "url_verification", "challenge": "XYZ"}
        response = client.post("/slack/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"challenge": "XYZ"}

    def test_processes_modal_form_submissions(self, client, mock_webhook_handler):
        """Test Slack events handler delegates view_submission."""
        mock_webhook_handler.handle_modal_submission.return_value = {"status": "ok"}
        payload = {"type": "view_submission"}
        response = client.post("/slack/events", json=payload)

        assert response.status_code == 200
        mock_webhook_handler.handle_modal_submission.assert_called_once_with(payload)

    def test_ignores_unsupported_slack_event_types(self, client):
        """Test Slack events handler ignores unknown event types."""
        payload = {"type": "unknown"}
        response = client.post("/slack/events", json=payload)

        assert response.status_code == 200
        assert response.json() == {"status": "ignored"}


@patch("src.emojismith.app.AsyncOpenAI")
@patch("src.emojismith.app.AsyncWebClient")
def test_configures_webhook_handler_with_environment_credentials(
    mock_slack_client, mock_openai_client, monkeypatch
):
    """Test create_webhook_handler sets up Slack client with token."""
    monkeypatch.setenv("SLACK_BOT_TOKEN", "test-token")
    monkeypatch.setenv("SLACK_SIGNING_SECRET", "test-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "openai")
    from src.emojismith.app import create_webhook_handler

    handler, security_service = create_webhook_handler()
    mock_slack_client.assert_called_once_with(token="test-token")
    mock_openai_client.assert_called_once_with(api_key="openai")
    # Handler exposes the message action handling interface
    assert hasattr(handler, "handle_message_action")
    # Security service should be returned
    assert security_service is not None
