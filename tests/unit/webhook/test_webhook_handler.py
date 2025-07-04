"""Tests for simplified webhook handler (package Lambda)."""

from unittest.mock import AsyncMock

import pytest

from webhook.handler import WebhookHandler


@pytest.mark.unit()
class TestWebhookHandler:
    """Test webhook handler for package Lambda."""

    @pytest.fixture()
    def mock_slack_repo(self):
        return AsyncMock()

    @pytest.fixture()
    def mock_job_queue(self):
        return AsyncMock()

    @pytest.fixture()
    def webhook_handler(self, mock_slack_repo, mock_job_queue):
        return WebhookHandler(slack_repo=mock_slack_repo, job_queue=mock_job_queue)

    async def test_handles_message_action_opens_modal_immediately(
        self, webhook_handler, mock_slack_repo
    ):
        """Test webhook handler opens modal immediately for fast response."""
        # Arrange
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "123456789.987654321.abcdefghijklmnopqrstuvwxyz",
            "user": {"id": "U12345", "name": "testuser"},
            "channel": {"id": "C67890", "name": "general"},
            "message": {
                "text": "Just deployed on Friday afternoon!",
                "ts": "1234567890.123456",
                "user": "U98765",
            },
            "team": {"id": "T11111"},
        }

        # Act
        result = await webhook_handler.handle_message_action(payload)

        # Assert
        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()
        view = mock_slack_repo.open_modal.call_args.kwargs["view"]
        block_ids = [b.get("block_id") for b in view["blocks"]]
        assert "emoji_name" in block_ids
        assert "emoji_description" in block_ids
        assert "style_preferences" in block_ids
        assert "toggle_advanced" in block_ids

    async def test_message_action_accepts_extra_team_fields(
        self, webhook_handler, mock_slack_repo
    ):
        """Team objects may include additional fields beyond the schema."""

        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {"text": "extra team", "user": "U1", "ts": "123.456"},
            "channel": {"id": "C1"},
            "team": {"id": "T1", "domain": "example"},
        }

        result = await webhook_handler.handle_message_action(payload)

        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

    async def test_handles_modal_submission_queues_emoji_job(
        self, webhook_handler, mock_job_queue
    ):
        """Test modal submission queues emoji generation job."""
        # Arrange
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_name": {"name": {"value": "facepalm"}},
                        "emoji_description": {"description": {"value": "facepalm"}},
                        "share_location": {
                            "share_location_select": {
                                "selected_option": {"value": "channel"}
                            }
                        },
                        "instruction_visibility": {
                            "visibility_select": {
                                "selected_option": {"value": "visible"}
                            }
                        },
                        "image_size": {
                            "size_select": {"selected_option": {"value": "512x512"}}
                        },
                        "style_preferences": {
                            "style_select": {"selected_option": {"value": "cartoon"}},
                            "detail_select": {"selected_option": {"value": "simple"}},
                        },
                        "color_scheme": {
                            "color_select": {"selected_option": {"value": "auto"}}
                        },
                        "tone": {"tone_select": {"selected_option": {"value": "fun"}}},
                    }
                },
                "private_metadata": (
                    '{"message_text": "test", "user_id": "U123", '
                    '"channel_id": "C123", "timestamp": "123.456", '
                    '"team_id": "T123"}'
                ),
            },
        }

        # Act
        result = await webhook_handler.handle_modal_submission(modal_payload)

        # Assert
        assert result == {"response_action": "clear"}
        mock_job_queue.enqueue_job.assert_called_once()

    async def test_validates_callback_id_in_payload(self, webhook_handler):
        """Test webhook handler validates correct callback ID."""
        # Arrange
        invalid_payload = {
            "type": "message_action",
            "callback_id": "wrong_callback_id",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {"text": "test", "user": "U1", "ts": "123.456"},
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
        }

        # Act & Assert
        with pytest.raises(ValueError, match="Invalid callback_id"):
            await webhook_handler.handle_message_action(invalid_payload)

    def test_validate_description_checks_word_count(self, webhook_handler):
        """Test description validation checks word count."""
        # Too few words
        is_valid, error = webhook_handler._validate_description("two words")
        assert not is_valid
        assert "at least 3 words" in error

        # Valid word count
        is_valid, error = webhook_handler._validate_description("this is a valid description")
        assert is_valid
        assert error == ""

    def test_validate_description_checks_prohibited_keywords(self, webhook_handler):
        """Test description validation rejects text/number requests."""
        prohibited_descriptions = [
            "text saying hello world",
            "write the word awesome",
            "letters ABC in bold",
            "numbers 1 2 3",
            "writing that says cool",
        ]
        
        for desc in prohibited_descriptions:
            is_valid, error = webhook_handler._validate_description(desc)
            assert not is_valid
            assert "cannot contain readable text or numbers" in error

    def test_validate_description_checks_length(self, webhook_handler):
        """Test description validation checks character length."""
        # Too short
        is_valid, error = webhook_handler._validate_description("short")
        assert not is_valid
        assert "too short" in error

        # Too long
        long_desc = "a" * 101
        is_valid, error = webhook_handler._validate_description(long_desc)
        assert not is_valid
        assert "too long" in error

        # Valid length
        is_valid, error = webhook_handler._validate_description("a happy smiling sun with sunglasses")
        assert is_valid
        assert error == ""

    async def test_modal_submission_validates_description(self, webhook_handler, mock_job_queue):
        """Test modal submission validates description content."""
        # Arrange - payload with invalid description (contains text request)
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_name": {"name": {"value": "invalid"}},
                        "emoji_description": {
                            "description": {"value": "text saying hello"}
                        },
                        "style_preferences": {
                            "style_select": {"selected_option": {"value": "cartoon"}},
                            "detail_select": {"selected_option": {"value": "simple"}},
                        },
                    }
                },
                "private_metadata": (
                    '{"message_text": "test", "user_id": "U123", '
                    '"channel_id": "C123", "timestamp": "123.456", '
                    '"team_id": "T123"}'
                ),
            },
        }

        # Act & Assert
        with pytest.raises(ValueError, match="cannot contain readable text or numbers"):
            await webhook_handler.handle_modal_submission(modal_payload)

    def test_get_style_hint_returns_correct_hints(self, webhook_handler):
        """Test style hints are returned for each style."""
        assert "cartoon" in webhook_handler._get_style_hint("cartoon")
        assert "realistic" in webhook_handler._get_style_hint("realistic")
        assert "minimalist" in webhook_handler._get_style_hint("minimalist")
        assert "pixel" in webhook_handler._get_style_hint("pixel")
        # Default hint for unknown style
        assert "Describe visual elements" in webhook_handler._get_style_hint("unknown")

    async def test_handles_slack_api_error_gracefully(
        self, webhook_handler, mock_slack_repo
    ):
        """Test webhook handler handles Slack API errors gracefully."""
        # Arrange
        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {"text": "test", "user": "U1", "ts": "123.456"},
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
        }
        mock_slack_repo.open_modal.side_effect = Exception("Slack API error")

        # Act
        result = await webhook_handler.handle_message_action(payload)

        # Assert
        assert result["status"] == "error"
        assert "Failed to create emoji" in result["error"]

    async def test_message_action_accepts_extra_message_fields(
        self, webhook_handler, mock_slack_repo
    ):
        """Message payloads may include additional fields beyond the schema."""

        payload = {
            "type": "message_action",
            "callback_id": "create_emoji_reaction",
            "trigger_id": "TRIG",
            "user": {"id": "U2", "name": "testuser"},
            "message": {
                "text": "extra fields",
                "user": "U1",
                "ts": "123.456",
                "type": "message",
                "client_msg_id": "abc123",
            },
            "channel": {"id": "C1"},
            "team": {"id": "T1"},
        }

        result = await webhook_handler.handle_message_action(payload)

        assert result == {"status": "ok"}
        mock_slack_repo.open_modal.assert_called_once()

    async def test_handles_block_actions_toggle_advanced(
        self, webhook_handler, mock_slack_repo
    ):
        """Test toggle advanced options button updates modal."""
        # Arrange
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": "toggle_advanced",
                    "value": "show",
                }
            ],
            "view": {
                "id": "V123456",
                "private_metadata": (
                    '{"message_text": "test emoji", "user_id": "U123", '
                    '"channel_id": "C123", "timestamp": "123.456", '
                    '"team_id": "T123"}'
                ),
            },
        }

        # Act
        result = await webhook_handler.handle_block_actions(payload)

        # Assert
        assert result == {}
        mock_slack_repo.update_modal.assert_called_once()
        view = mock_slack_repo.update_modal.call_args.kwargs["view"]

        # Check that advanced blocks are present
        block_ids = [b.get("block_id") for b in view["blocks"]]
        assert "color_scheme" in block_ids
        assert "tone" in block_ids
        assert "share_location" in block_ids
        assert "instruction_visibility" in block_ids
        assert "image_size" in block_ids

        # Check toggle button changed to "Hide"
        toggle_block = next(
            b for b in view["blocks"] if b.get("block_id") == "toggle_advanced"
        )
        assert "Hide Advanced Options" in toggle_block["elements"][0]["text"]["text"]
        assert toggle_block["elements"][0]["value"] == "hide"

    async def test_modal_submission_with_optional_advanced_fields(
        self, webhook_handler, mock_job_queue
    ):
        """Test modal submission works without advanced fields (using defaults)."""
        # Arrange - minimal payload without advanced fields
        modal_payload = {
            "type": "view_submission",
            "view": {
                "callback_id": "emoji_creation_modal",
                "state": {
                    "values": {
                        "emoji_name": {"name": {"value": "thumbsup"}},
                        "emoji_description": {
                            "description": {"value": "thumbs up gesture"}
                        },
                        "style_preferences": {
                            "style_select": {"selected_option": {"value": "cartoon"}},
                            "detail_select": {"selected_option": {"value": "simple"}},
                        },
                        # Advanced fields not present - should use defaults
                    }
                },
                "private_metadata": (
                    '{"message_text": "great job!", "user_id": "U456", '
                    '"channel_id": "C456", "timestamp": "456.789", '
                    '"team_id": "T456"}'
                ),
            },
        }

        # Act
        result = await webhook_handler.handle_modal_submission(modal_payload)

        # Assert
        assert result == {"response_action": "clear"}
        mock_job_queue.enqueue_job.assert_called_once()

        # Verify defaults were used
        job = mock_job_queue.enqueue_job.call_args[0][0]
        assert job.sharing_preferences.share_location.value == "channel"  # default
        assert (
            job.sharing_preferences.instruction_visibility.value == "EVERYONE"
        )  # default show -> EVERYONE
        assert (
            job.sharing_preferences.image_size.value == "EMOJI_SIZE"
        )  # default 512 -> EMOJI_SIZE
        assert job.style_preferences.color_scheme.value == "auto"  # default
        assert job.style_preferences.tone.value == "fun"  # default
