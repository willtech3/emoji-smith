import os
import pytest
from io import BytesIO
from PIL import Image
from slack_sdk.web.async_client import AsyncWebClient

from emojismith.infrastructure.slack.slack_file_sharing import (
    SlackFileSharingRepository,
)
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.value_objects import EmojiSharingPreferences


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("SLACK_TEST_BOT_TOKEN") or not os.getenv("SLACK_TEST_CHANNEL_ID"),
    reason="Slack test token or channel ID not configured",
)
async def test_share_emoji_file_real_slack():
    """Share a tiny emoji file in Slack and expect a file URL."""
    token = os.environ["SLACK_TEST_BOT_TOKEN"]
    channel_id = os.environ["SLACK_TEST_CHANNEL_ID"]

    client = AsyncWebClient(token=token)
    repo = SlackFileSharingRepository(slack_client=client)

    img = Image.new("RGB", (16, 16), color="red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    emoji = GeneratedEmoji(image_data=buf.getvalue(), name="integration_test")
    prefs = EmojiSharingPreferences.default_for_context()

    result = await repo.share_emoji_file(
        emoji=emoji,
        channel_id=channel_id,
        preferences=prefs,
        requester_user_id="U000000",
    )

    assert result.success is True
    assert result.file_url
