import os
import pytest
from io import BytesIO
from PIL import Image
from slack_sdk.web.async_client import AsyncWebClient

from emojismith.infrastructure.slack.slack_file_sharing import (
    SlackFileSharingRepository,
)
from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    ShareLocation,
    InstructionVisibility,
    ImageSize,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_slack_file_upload_and_thread_creation() -> None:
    """Upload an emoji file to Slack and create a thread if credentials provided."""
    token = os.getenv("SLACK_TEST_TOKEN")
    channel = os.getenv("SLACK_TEST_CHANNEL")

    if not token or not channel:
        pytest.skip("Slack integration credentials not configured")

    client = AsyncWebClient(token=token)
    repo = SlackFileSharingRepository(client)

    # Build small test emoji
    img = Image.new("RGBA", (128, 128), "green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    emoji = GeneratedEmoji(name="integration_test", image_data=buf.getvalue())

    prefs = EmojiSharingPreferences(
        share_location=ShareLocation.NEW_THREAD,
        instruction_visibility=InstructionVisibility.EVERYONE,
        image_size=ImageSize.EMOJI_SIZE,
    )

    result = await repo.share_emoji_file(
        emoji=emoji,
        channel_id=channel,
        preferences=prefs,
        requester_user_id="U00000000",
        original_message_ts=None,
    )

    assert result.success is True
    assert result.file_url is not None

    assert result.thread_ts is not None
