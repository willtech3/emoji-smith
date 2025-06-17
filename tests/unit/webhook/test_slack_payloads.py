import pytest
from webhook.domain.slack_payloads import MessageActionPayload


class TestSlackPayloadParsing:
    """Tests for Slack payload parsing utilities."""

    def test_message_action_payload_parses_message_with_extra_fields(self):
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "trigger123",
            "user": {"id": "U1", "name": "tester"},
            "channel": {"id": "C1", "name": "general"},
            "message": {
                "type": "message",
                "text": "example",
                "ts": "123.456",
                "user": "U2",
            },
            "team": {"id": "T1"},
        }

        result = MessageActionPayload.from_dict(payload)

        assert result.message.text == "example"
        assert result.message.ts == "123.456"
        assert result.message.user == "U2"
