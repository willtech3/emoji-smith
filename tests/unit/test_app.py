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
        with patch(
            "src.emojismith.app.create_webhook_handler",
            return_value=mock_webhook_handler,
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

    def test_slack_events_endpoint_accepts_post(self, client, mock_webhook_handler):
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

    def test_slack_events_endpoint_rejects_get(self, client):
        """Test Slack events endpoint rejects GET requests."""
        response = client.get("/slack/events")

        assert response.status_code == 405  # Method Not Allowed
