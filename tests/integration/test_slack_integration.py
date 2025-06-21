import os
from io import BytesIO
from PIL import Image
import pytest
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


@pytest.fixture(scope="session")
def slack_token() -> str:
    token = os.getenv("SLACK_TEST_BOT_TOKEN")
    if not token:
        pytest.skip("Slack test token not configured")
    return token


@pytest.fixture(scope="session")
def slack_client(slack_token: str) -> AsyncWebClient:
    return AsyncWebClient(token=slack_token)


@pytest.fixture(scope="session")
def slack_repo(slack_client: AsyncWebClient) -> SlackFileSharingRepository:
    return SlackFileSharingRepository(slack_client)


@pytest.fixture(scope="session")
def slack_slack_test_channel() -> str:
    channel = os.getenv("SLACK_TEST_CHANNEL_ID")
    if not channel:
        pytest.skip("Slack test channel not configured")
    return channel


@pytest.fixture(scope="session")
def slack_slack_test_user_id() -> str:
    user = os.getenv("SLACK_TEST_USER_ID")
    if not user:
        pytest.skip("Slack test user not configured")
    return user


@pytest.fixture()
def sample_emoji() -> GeneratedEmoji:
    img = Image.new("RGBA", (128, 128), "green")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return GeneratedEmoji(name="integration_test_emoji", image_data=buf.getvalue())


@pytest.mark.asyncio
async def test_share_emoji_new_thread(
    slack_repo, slack_client, slack_test_channel, slack_test_user_id, sample_emoji
):
    message = await slack_client.chat_postMessage(
        channel=slack_test_channel, text="Integration test start"
    )
    original_ts = message["ts"]

    prefs = EmojiSharingPreferences(
        share_location=ShareLocation.NEW_THREAD,
        instruction_visibility=InstructionVisibility.EVERYONE,
        image_size=ImageSize.EMOJI_SIZE,
    )

    result = await slack_repo.share_emoji_file(
        emoji=sample_emoji,
        channel_id=slack_test_channel,
        preferences=prefs,
        requester_user_id=slack_test_user_id,
        original_message_ts=original_ts,
    )

    assert result.success
    assert result.thread_ts
    assert result.file_url


@pytest.mark.asyncio
async def test_share_emoji_existing_thread(
    slack_repo, slack_client, slack_test_channel, slack_test_user_id, sample_emoji
):
    thread_msg = await slack_client.chat_postMessage(
        channel=slack_test_channel, text="Existing thread starter"
    )
    thread_ts = thread_msg["ts"]

    prefs = EmojiSharingPreferences(
        share_location=ShareLocation.THREAD,
        instruction_visibility=InstructionVisibility.SUBMITTER_ONLY,
        image_size=ImageSize.EMOJI_SIZE,
        thread_ts=thread_ts,
    )

    result = await slack_repo.share_emoji_file(
        emoji=sample_emoji,
        channel_id=slack_test_channel,
        preferences=prefs,
        requester_user_id=slack_test_user_id,
    )

    assert result.success
    assert result.thread_ts == thread_ts
    assert result.file_url


@pytest.mark.asyncio
async def test_share_fails_with_invalid_token(slack_test_channel, sample_emoji):
    invalid_client = AsyncWebClient(token="xoxb-invalid-token")
    repo = SlackFileSharingRepository(invalid_client)
    prefs = EmojiSharingPreferences(
        share_location=ShareLocation.NEW_THREAD,
        instruction_visibility=InstructionVisibility.EVERYONE,
        image_size=ImageSize.EMOJI_SIZE,
    )

    result = await repo.share_emoji_file(
        emoji=sample_emoji,
        channel_id=slack_test_channel,
        preferences=prefs,
        requester_user_id="U000000",
    )

    assert not result.success
    assert result.error
