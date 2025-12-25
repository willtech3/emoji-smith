"""Tests for SlackWebhookHandler and WebhookEventProcessor."""

import json
from unittest.mock import AsyncMock

import pytest

from emojismith.application.handlers.slack_webhook_handler import WebhookEventProcessor
from emojismith.application.modal_builder import EmojiCreationModalBuilder
from shared.domain.repositories import JobQueueProducer, SlackModalRepository


@pytest.mark.unit()
class TestGenerateEmojiName:
    """Tests for WebhookEventProcessor._generate_emoji_name static method."""

    def test_generates_slug_from_simple_description(self):
        """Simple description produces lowercase slug with hash suffix."""
        name = WebhookEventProcessor._generate_emoji_name("Happy Cat")
        assert name.startswith("happy_cat_")
        assert len(name) <= 32

    def test_removes_special_characters(self):
        """Special characters are stripped from description."""
        name = WebhookEventProcessor._generate_emoji_name("A @#$% test!")
        assert "@" not in name
        assert "#" not in name
        assert "!" not in name
        assert name.startswith("a_test_")

    def test_handles_unicode_and_emoji(self):
        """Unicode and emoji are removed, leaving alphanumeric."""
        name = WebhookEventProcessor._generate_emoji_name("Happy 🎉 Party!")
        assert "🎉" not in name
        assert name.startswith("happy_party_")

    def test_truncates_long_descriptions(self):
        """Long descriptions are truncated to fit 32-char limit."""
        long_desc = "A very long description that exceeds the maximum length limit"
        name = WebhookEventProcessor._generate_emoji_name(long_desc)
        assert len(name) <= 32

    def test_generates_unique_hash_suffix(self):
        """Different descriptions produce different hash suffixes."""
        name1 = WebhookEventProcessor._generate_emoji_name("Happy Cat")
        name2 = WebhookEventProcessor._generate_emoji_name("Happy Dog")
        # Same prefix but different hashes
        assert name1.startswith("happy_")
        assert name2.startswith("happy_")
        assert name1 != name2

    def test_same_description_produces_same_name(self):
        """Same description always produces the same emoji name."""
        name1 = WebhookEventProcessor._generate_emoji_name("Dancing Banana")
        name2 = WebhookEventProcessor._generate_emoji_name("Dancing Banana")
        assert name1 == name2

    def test_handles_consecutive_spaces(self):
        """Consecutive spaces are collapsed to single underscore."""
        name = WebhookEventProcessor._generate_emoji_name("hello    world")
        # Should not have consecutive underscores
        assert "__" not in name

    def test_strips_leading_trailing_underscores(self):
        """Leading and trailing underscores are stripped."""
        name = WebhookEventProcessor._generate_emoji_name("  hello  ")
        # Should not start or end with underscore before hash
        base_name = name.rsplit("_", 1)[0]
        assert not base_name.startswith("_")
        assert not base_name.endswith("_")


@pytest.mark.unit()
class TestModalSubmissionAutoGeneratesName:
    """Tests for modal submission with empty emoji name."""

    @pytest.fixture()
    def mock_slack_repo(self):
        return AsyncMock(spec=SlackModalRepository)

    @pytest.fixture()
    def mock_job_queue(self):
        return AsyncMock(spec=JobQueueProducer)

    @pytest.fixture()
    def processor(self, mock_slack_repo, mock_job_queue):
        return WebhookEventProcessor(
            slack_repo=mock_slack_repo,
            job_queue=mock_job_queue,
            google_enabled=True,
        )

    def _make_submission_payload(
        self, description: str, emoji_name: str | None = None
    ) -> dict:
        """Create a view_submission payload for testing."""
        state_values = {
            "emoji_description": {"description": {"value": description}},
        }
        # Only include emoji_name block if provided (simulates collapsed view)
        if emoji_name is not None:
            state_values["emoji_name"] = {"name": {"value": emoji_name}}

        return {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {"values": state_values},
                "private_metadata": json.dumps(
                    {
                        "message_text": "test message",
                        "user_id": "U123",
                        "channel_id": "C456",
                        "timestamp": "111.222",
                        "team_id": "T789",
                    }
                ),
            },
        }

    @pytest.mark.asyncio()
    async def test_auto_generates_name_when_emoji_name_empty(
        self, processor, mock_job_queue
    ):
        """When emoji_name is empty, auto-generate from description."""
        payload = self._make_submission_payload(
            description="A happy dancing banana",
            emoji_name="",  # Empty string
        )
        body = json.dumps(payload).encode()

        result = await processor.process(body)

        assert result == {"response_action": "clear"}
        mock_job_queue.enqueue_job.assert_awaited_once()
        job = mock_job_queue.enqueue_job.call_args.args[0]
        # Should have auto-generated name from description
        assert job.emoji_name.startswith("a_happy_dancing_banan")
        assert len(job.emoji_name) <= 32

    @pytest.mark.asyncio()
    async def test_auto_generates_name_when_block_missing(
        self, processor, mock_job_queue
    ):
        """When emoji_name block is missing (collapsed view), auto-generate."""
        payload = self._make_submission_payload(
            description="Facepalm reaction",
            emoji_name=None,  # Block not present
        )
        body = json.dumps(payload).encode()

        result = await processor.process(body)

        assert result == {"response_action": "clear"}
        mock_job_queue.enqueue_job.assert_awaited_once()
        job = mock_job_queue.enqueue_job.call_args.args[0]
        # Should have auto-generated name
        assert job.emoji_name.startswith("facepalm_reaction_")

    @pytest.mark.asyncio()
    async def test_uses_provided_name_when_present(self, processor, mock_job_queue):
        """When emoji_name is provided, use it instead of auto-generating."""
        payload = self._make_submission_payload(
            description="A happy dancing banana",
            emoji_name="custom_banana",
        )
        body = json.dumps(payload).encode()

        result = await processor.process(body)

        assert result == {"response_action": "clear"}
        mock_job_queue.enqueue_job.assert_awaited_once()
        job = mock_job_queue.enqueue_job.call_args.args[0]
        # Should use provided name
        assert job.emoji_name == "custom_banana"


@pytest.mark.unit()
class TestMessageActionModalDefaultsToNanoBananaPro:
    """Tests that the Slack modal defaults to Nano Banana Pro in production-like config.

    The webhook Lambda does not have AI provider API keys injected, but the worker does.
    The modal should still default to the best available model (Nano Banana Pro).
    """

    @pytest.fixture()
    def mock_slack_repo(self):
        return AsyncMock(spec=SlackModalRepository)

    @pytest.fixture()
    def mock_job_queue(self):
        return AsyncMock(spec=JobQueueProducer)

    @pytest.fixture()
    def processor(self, mock_slack_repo, mock_job_queue):
        # Webhook Lambda does not receive provider API keys.
        return WebhookEventProcessor(
            slack_repo=mock_slack_repo,
            job_queue=mock_job_queue,
            google_enabled=True,
        )

    @pytest.mark.asyncio()
    async def test_message_action_modal_shows_nano_banana_pro_selected_by_default(
        self, processor, mock_slack_repo
    ):
        payload = {
            "type": "message_action",
            "trigger_id": "TRIGGER",
            "message": {"text": "hello", "ts": "111.222", "user": "U999"},
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
        }

        await processor.process(json.dumps(payload).encode())

        mock_slack_repo.open_modal.assert_awaited_once()
        view = mock_slack_repo.open_modal.call_args.kwargs["view"]
        provider_block = next(
            (
                b
                for b in view["blocks"]
                if b.get("block_id") == EmojiCreationModalBuilder.IMAGE_PROVIDER_BLOCK
            ),
            None,
        )
        assert provider_block is not None

        element = provider_block["element"]
        option_values = [o["value"] for o in element["options"]]
        assert "google_gemini" in option_values
        assert "openai" in option_values
        assert element["initial_option"]["value"] == "google_gemini"
        assert "Nano Banana Pro" in element["initial_option"]["text"]["text"]
