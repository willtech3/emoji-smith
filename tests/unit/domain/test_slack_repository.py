"""Tests for SlackRepository protocol interface."""

from emojismith.domain.repositories.slack_repository import (
    SlackModalRepository,
    SlackEmojiRepository,
    SlackRepository,
)


def test_slack_repository_protocol_methods_exist() -> None:
    """Slack repository protocols define required methods."""
    assert hasattr(SlackModalRepository, "open_modal")
    assert hasattr(SlackEmojiRepository, "upload_emoji")
    assert hasattr(SlackEmojiRepository, "add_emoji_reaction")
    # Combined interface should include all modal and emoji methods
    assert hasattr(SlackRepository, "open_modal")
    assert hasattr(SlackRepository, "upload_emoji")
    assert hasattr(SlackRepository, "add_emoji_reaction")
