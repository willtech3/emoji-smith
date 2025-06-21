from src.emojismith.domain.entities.queue_message import MessageType, QueueMessage
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


class TestQueueMessage:
    def test_round_trip_serialization(self) -> None:
        job = EmojiGenerationJob.create_new(
            user_description="desc",
            emoji_name="name",
            message_text="msg",
            user_id="U1",
            channel_id="C1",
            timestamp="123",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )
        msg = QueueMessage(message_type=MessageType.EMOJI_GENERATION, payload=job)
        data = msg.to_dict()
        restored = QueueMessage.from_dict(data)
        assert restored.message_type == MessageType.EMOJI_GENERATION
        assert isinstance(restored.payload, EmojiGenerationJob)
        assert restored.payload.job_id == job.job_id

    def test_should_retry_returns_true_when_under_max_retries(self) -> None:
        """Message should be retried when retry count is below maximum."""
        job = EmojiGenerationJob.create_new(
            user_description="desc",
            emoji_name="name",
            message_text="msg",
            user_id="U1",
            channel_id="C1",
            timestamp="123",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )
        msg = QueueMessage(
            message_type=MessageType.EMOJI_GENERATION, payload=job, retry_count=0
        )
        assert msg.should_retry() is True

    def test_should_retry_returns_false_when_at_max_retries(self) -> None:
        """Message should not be retried when retry count reaches maximum."""
        job = EmojiGenerationJob.create_new(
            user_description="desc",
            emoji_name="name",
            message_text="msg",
            user_id="U1",
            channel_id="C1",
            timestamp="123",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )
        msg = QueueMessage(
            message_type=MessageType.EMOJI_GENERATION,
            payload=job,
            retry_count=3,  # Assuming MAX_RETRIES is 3
        )
        assert msg.should_retry() is False

    def test_with_retry_creates_new_message_with_incremented_count(self) -> None:
        """New message should have incremented retry count."""
        job = EmojiGenerationJob.create_new(
            user_description="desc",
            emoji_name="name",
            message_text="msg",
            user_id="U1",
            channel_id="C1",
            timestamp="123",
            team_id="T1",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )
        original_msg = QueueMessage(
            message_type=MessageType.EMOJI_GENERATION, payload=job, retry_count=1
        )

        new_msg = original_msg.with_retry()

        assert new_msg.retry_count == 2
        assert new_msg.message_type == original_msg.message_type
        assert new_msg.payload == original_msg.payload
        assert original_msg.retry_count == 1  # Original unchanged
