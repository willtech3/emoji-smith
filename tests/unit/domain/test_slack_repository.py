"""Tests for SlackRepository protocol interface."""

from shared.domain.repositories.slack_repository import (
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


def test_interface_composition() -> None:
    """Verify SlackRepository properly extends both modal and emoji interfaces."""
    assert issubclass(SlackRepository, SlackModalRepository)
    assert issubclass(SlackRepository, SlackEmojiRepository)


def test_runtime_checkable_protocols() -> None:
    """Verify protocols support runtime type checking."""
    from unittest.mock import Mock
    
    # Mock implementations should satisfy protocol checks
    modal_mock = Mock()
    modal_mock.open_modal = Mock()
    assert isinstance(modal_mock, SlackModalRepository)
    
    emoji_mock = Mock()
    emoji_mock.upload_emoji = Mock()
    emoji_mock.add_emoji_reaction = Mock()
    assert isinstance(emoji_mock, SlackEmojiRepository)
