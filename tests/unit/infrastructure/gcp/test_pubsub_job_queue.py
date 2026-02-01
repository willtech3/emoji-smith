from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from google.cloud import pubsub_v1

from shared.domain.dtos import EmojiGenerationJobDto


@pytest.mark.unit()
class TestPubSubJobQueue:
    @pytest.mark.asyncio()
    async def test_enqueue_job_publishes_serialized_job_to_topic(self, monkeypatch):
        """Jobs should be JSON-serialized and published to the configured topic."""
        monkeypatch.setenv("PUBSUB_PROJECT", "test-project")
        monkeypatch.setenv("PUBSUB_TOPIC", "emoji-smith-jobs")

        mock_publisher = MagicMock()
        mock_publisher.topic_path.return_value = (
            "projects/test-project/topics/emoji-smith-jobs"
        )
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-123"
        mock_publisher.publish.return_value = mock_future

        monkeypatch.setattr(
            pubsub_v1,
            "PublisherClient",
            MagicMock(return_value=mock_publisher),
        )

        from emojismith.infrastructure.gcp.pubsub_job_queue import PubSubJobQueue

        job_queue = PubSubJobQueue()

        job = EmojiGenerationJobDto(
            job_id="job_123",
            user_description="facepalm reaction",
            message_text="Just deployed on Friday!",
            user_id="U12345",
            channel_id="C67890",
            timestamp="1234567890.123456",
            team_id="T11111",
            emoji_name="facepalm_reaction",
            status="PENDING",
            sharing_preferences={"share_location": "channel"},
            created_at="2026-01-31T00:00:00+00:00",
            trace_id="trace_123",
            image_provider="openai",
        )

        message_id = await job_queue.enqueue_job(job)

        assert message_id == "msg-123"

        mock_publisher.topic_path.assert_called_once_with(
            "test-project", "emoji-smith-jobs"
        )
        mock_publisher.publish.assert_called_once()

        topic_path, data = mock_publisher.publish.call_args.args
        assert topic_path == "projects/test-project/topics/emoji-smith-jobs"

        payload = json.loads(data.decode("utf-8"))
        assert payload["job_id"] == "job_123"
        assert payload["user_description"] == "facepalm reaction"
        assert payload["trace_id"] == "trace_123"
        assert payload["image_provider"] == "openai"
