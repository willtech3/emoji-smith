"""Regression tests for webhook failures that left users without a result."""

import json
from unittest.mock import AsyncMock

import pytest

from emojismith.application.handlers.slack_webhook_handler import (
    WebhookEventProcessor,
)

SLACK_PRIVATE_METADATA_LIMIT = 3000


def _message_action(message: dict) -> bytes:
    return json.dumps(
        {
            "type": "message_action",
            "trigger_id": "trigger",
            "user": {"id": "U1"},
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
            "message": message,
        }
    ).encode()


@pytest.fixture()
def slack_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def job_queue() -> AsyncMock:
    return AsyncMock()


@pytest.fixture()
def processor(slack_repo, job_queue) -> WebhookEventProcessor:
    return WebhookEventProcessor(slack_repo=slack_repo, job_queue=job_queue)


def _opened_view(slack_repo: AsyncMock) -> dict:
    return slack_repo.open_modal.call_args.kwargs["view"]


@pytest.mark.unit()
class TestMessageActionModalMetadata:
    @pytest.mark.parametrize(
        "text",
        ["日本語のメッセージ" * 200, "🎉" * 1500, "\n" * 4000, '"' * 4000],
        ids=["cjk", "emoji", "newlines", "quotes"],
    )
    async def test_message_action_with_long_message_keeps_metadata_within_limit(
        self, processor, slack_repo, text
    ):
        """Slack refuses to open a modal whose private_metadata exceeds 3000."""
        await processor.process(_message_action({"text": text, "ts": "111.222"}))

        metadata = _opened_view(slack_repo)["private_metadata"]
        assert len(metadata) <= SLACK_PRIVATE_METADATA_LIMIT
        assert json.loads(metadata)["channel_id"] == "C1"

    async def test_message_action_with_short_message_preserves_full_text(
        self, processor, slack_repo
    ):
        await processor.process(_message_action({"text": "ship it 🚀", "ts": "1.2"}))

        metadata = json.loads(_opened_view(slack_repo)["private_metadata"])
        assert metadata["message_text"] == "ship it 🚀"

    async def test_message_action_on_thread_reply_records_parent_thread(
        self, processor, slack_repo
    ):
        """Replies must be posted under the thread parent, not the reply."""
        await processor.process(
            _message_action({"text": "reply", "ts": "200.2", "thread_ts": "100.1"})
        )

        metadata = json.loads(_opened_view(slack_repo)["private_metadata"])
        assert metadata["thread_ts"] == "100.1"

    async def test_message_action_on_top_level_message_has_no_thread(
        self, processor, slack_repo
    ):
        await processor.process(
            _message_action({"text": "parent", "ts": "100.1", "thread_ts": "100.1"})
        )

        metadata = json.loads(_opened_view(slack_repo)["private_metadata"])
        assert "thread_ts" not in metadata


@pytest.mark.unit()
class TestModalSubmissionFromThread:
    async def test_submission_from_thread_reply_shares_into_parent_thread(
        self, processor, slack_repo, job_queue
    ):
        await processor.process(
            _message_action({"text": "reply", "ts": "200.2", "thread_ts": "100.1"})
        )
        view = _opened_view(slack_repo)
        builder = processor._modal_builder
        submission = {
            "type": "view_submission",
            "view": {
                "private_metadata": view["private_metadata"],
                "state": {
                    "values": {
                        builder.DESCRIPTION_BLOCK: {
                            builder.DESCRIPTION_ACTION: {"value": "a happy cat"}
                        }
                    }
                },
            },
        }

        await processor.process(json.dumps(submission).encode())

        job = job_queue.enqueue_job.call_args.args[0]
        assert job.sharing_preferences["thread_ts"] == "100.1"

    async def test_submission_with_null_form_values_uses_defaults(
        self, processor, job_queue
    ):
        """Slack sends null, not a missing key, for untouched optional inputs."""
        builder = processor._modal_builder
        submission = {
            "type": "view_submission",
            "view": {
                "private_metadata": json.dumps(
                    {"user_id": "U1", "channel_id": "C1", "timestamp": "1.2"}
                ),
                "state": {
                    "values": {
                        builder.DESCRIPTION_BLOCK: {
                            builder.DESCRIPTION_ACTION: {"value": "a happy cat"}
                        },
                        builder.STYLE_TEXT_BLOCK: {
                            builder.STYLE_TEXT_ACTION: {"value": None}
                        },
                        builder.BACKGROUND_BLOCK: {
                            builder.BACKGROUND_ACTION: {"selected_option": None}
                        },
                        builder.IMAGE_PROVIDER_BLOCK: {
                            builder.PROVIDER_ACTION: {"selected_option": None}
                        },
                    }
                },
            },
        }

        response = await processor.process(json.dumps(submission).encode())

        assert response == {"response_action": "clear"}
        job = job_queue.enqueue_job.call_args.args[0]
        assert job.generation_preferences["background"] == "transparent"
        assert job.generation_preferences["style_text"] == ""
        assert job.image_provider == "google_gemini"
