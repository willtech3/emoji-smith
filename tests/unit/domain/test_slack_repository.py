"""Tests for SlackRepository protocol interface."""

from shared.domain.repositories.slack_repository import (
    SlackEmojiRepository,
    SlackModalRepository,
    SlackRepository,
)


def test_slack_repository_protocol_methods_exist() -> None:
    """SlackRepository protocol defines required methods."""
    assert hasattr(SlackRepository, "open_modal"), "open_modal must be defined"
    assert hasattr(SlackRepository, "upload_emoji"), "upload_emoji must be defined"
    assert hasattr(
        SlackRepository, "add_emoji_reaction"
    ), "add_emoji_reaction must be defined"


def test_interface_composition() -> None:
    """SlackRepository should extend both modal and emoji interfaces."""
    assert issubclass(SlackRepository, SlackModalRepository)
    assert issubclass(SlackRepository, SlackEmojiRepository)
