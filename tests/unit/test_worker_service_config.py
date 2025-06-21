import pytest
from emojismith.app import create_worker_emoji_service


def test_worker_service_requires_slack_token(monkeypatch):
    monkeypatch.delenv("SLACK_BOT_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(
        ValueError, match="SLACK_BOT_TOKEN environment variable is required"
    ):
        create_worker_emoji_service()


def test_worker_service_requires_openai_key(monkeypatch):
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-test")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(
        ValueError, match="OPENAI_API_KEY environment variable is required"
    ):
        create_worker_emoji_service()
