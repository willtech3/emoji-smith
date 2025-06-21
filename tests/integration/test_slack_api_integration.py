import os
from io import BytesIO
import pytest
from slack_sdk.web.async_client import AsyncWebClient
from PIL import Image

SLACK_BOT_TOKEN = os.getenv("SLACK_TEST_BOT_TOKEN")
TEST_CHANNEL = os.getenv("SLACK_TEST_CHANNEL_ID")


@pytest.fixture()
async def slack_client():
    if not SLACK_BOT_TOKEN or not TEST_CHANNEL:
        pytest.skip("Slack integration credentials not configured")
    client = AsyncWebClient(token=SLACK_BOT_TOKEN)
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_can_post_and_delete_message(slack_client):
    resp = await slack_client.chat_postMessage(
        channel=TEST_CHANNEL, text="integration test"
    )
    assert resp["ok"]
    ts = resp["ts"]
    delete_resp = await slack_client.chat_delete(channel=TEST_CHANNEL, ts=ts)
    assert delete_resp["ok"]


@pytest.mark.asyncio
async def test_can_upload_and_delete_file(slack_client):
    img = Image.new("RGBA", (128, 128), "blue")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    resp = await slack_client.files_upload_v2(
        channels=[TEST_CHANNEL], file=buf, filename="emoji.png"
    )
    assert resp["ok"]
    file_id = resp["file"]["id"]
    del_resp = await slack_client.files_delete(file=file_id)
    assert del_resp["ok"]
