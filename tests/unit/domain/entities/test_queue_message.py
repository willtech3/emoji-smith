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
