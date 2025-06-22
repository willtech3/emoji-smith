import pytest

from webhook.domain.slack_payloads import SlackChannel, MessageActionPayload


@pytest.mark.contract
class TestSlackChannel:
    """Tests for SlackChannel domain model."""

    def test_from_dict_extracts_required_fields(self):
        """SlackChannel.from_dict should extract id and name fields."""
        data = {"id": "C123456", "name": "general"}

        result = SlackChannel.from_dict(data)

        assert result.id == "C123456"
        assert result.name == "general"

    def test_from_dict_handles_missing_name(self):
        """SlackChannel.from_dict should handle missing optional name field."""
        data = {"id": "C123456"}

        result = SlackChannel.from_dict(data)

        assert result.id == "C123456"
        assert result.name is None

    def test_from_dict_ignores_extra_fields(self):
        """SlackChannel.from_dict should ignore unexpected extra fields."""
        data = {
            "id": "C123456",
            "name": "general",
            "topic": {"value": "Channel topic"},
            "purpose": {"value": "Channel purpose"},
            "is_member": True,
            "num_members": 42,
        }

        result = SlackChannel.from_dict(data)

        assert result.id == "C123456"
        assert result.name == "general"


@pytest.mark.contract
class TestMessageActionPayloadWithSlackChannel:
    """Tests for MessageActionPayload parsing with SlackChannel.from_dict()."""

    def test_message_action_payload_uses_channel_from_dict(self):
        """MessageActionPayload uses SlackChannel.from_dict() for robust parsing."""
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "trigger123",
            "user": {"id": "U1", "name": "tester"},
            "channel": {
                "id": "C1",
                "name": "general",
                "topic": {"value": "Extra field"},
                "is_member": True,
            },
            "message": {"text": "hello", "ts": "123.456", "user": "U2"},
            "team": {"id": "T1"},
        }

        result = MessageActionPayload.from_dict(payload)

        assert result.channel.id == "C1"
        assert result.channel.name == "general"
