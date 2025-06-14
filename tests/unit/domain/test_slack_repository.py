"""Tests for SlackRepository protocol interface."""

from emojismith.domain.repositories.slack_repository import SlackRepository


def test_slack_repository_protocol_methods_exist() -> None:
    """SlackRepository protocol defines required methods."""
    assert hasattr(SlackRepository, "open_modal"), "open_modal must be defined"
    assert hasattr(SlackRepository, "upload_emoji"), "upload_emoji must be defined"
    assert hasattr(
        SlackRepository, "add_emoji_reaction"
    ), "add_emoji_reaction must be defined"
