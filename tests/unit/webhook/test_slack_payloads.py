import pytest
from webhook.domain.slack_payloads import MessageActionPayload


class TestMessageActionPayload:
    def test_from_dict_ignores_extra_message_fields(self) -> None:
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "123",
            "user": {"id": "U1", "name": "user"},
            "channel": {"id": "C1", "name": "general"},
            "message": {
                "type": "message",
                "text": "hello",
                "ts": "123.456",
                "user": "U1",
                "extra": "ignore me",
            },
            "team": {"id": "T1"},
        }

        result = MessageActionPayload.from_dict(payload)

        assert result.message.text == "hello"
        assert result.message.ts == "123.456"
        assert result.message.user == "U1"
