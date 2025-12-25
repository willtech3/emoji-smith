"""Tests for EmojiCreationModalBuilder."""

import json

import pytest

from emojismith.application.modal_builder import EmojiCreationModalBuilder


@pytest.mark.unit()
class TestEmojiCreationModalBuilder:
    """Tests for EmojiCreationModalBuilder."""

    @pytest.fixture()
    def builder(self):
        """Default builder with Google not available (defaults to OpenAI)."""
        return EmojiCreationModalBuilder(
            default_provider="openai", google_available=False
        )

    @pytest.fixture()
    def builder_with_google(self):
        """Builder with Google available."""
        return EmojiCreationModalBuilder(
            default_provider="google_gemini", google_available=True
        )

    @pytest.fixture()
    def sample_metadata(self):
        return {
            "message_text": "Just shipped new feature!",
            "user_id": "U123456",
            "channel_id": "C123456",
            "timestamp": "1234567890.123456",
            "team_id": "T123456",
        }

    def test_build_collapsed_view_returns_valid_modal(self, builder, sample_metadata):
        view = builder.build_collapsed_view(sample_metadata)
        assert view["type"] == "modal"
        assert view["callback_id"] == "emoji_creation_modal"
        assert view["title"]["text"] == "Create Emoji"
        assert "Generate" in view["submit"]["text"]  # May include emoji
        assert view["close"]["text"] == "Cancel"

    def test_build_collapsed_view_contains_description_input(
        self, builder, sample_metadata
    ):
        view = builder.build_collapsed_view(sample_metadata)
        blocks = view["blocks"]

        # Find description block
        description_block = next(
            (b for b in blocks if b.get("block_id") == builder.DESCRIPTION_BLOCK), None
        )
        assert description_block is not None
        assert description_block["type"] == "input"
        assert description_block["element"]["type"] == "plain_text_input"
        assert description_block["element"]["multiline"] is True

    def test_build_collapsed_view_contains_image_provider(
        self, builder, sample_metadata
    ):
        """Image provider should be available in collapsed/basic view."""
        view = builder.build_collapsed_view(sample_metadata)
        blocks = view["blocks"]

        provider_block = next(
            (b for b in blocks if b.get("block_id") == builder.IMAGE_PROVIDER_BLOCK),
            None,
        )
        assert provider_block is not None
        assert provider_block["type"] == "input"
        assert provider_block["label"]["text"] == "Image Model"

    def test_build_collapsed_view_contains_toggle_button(
        self, builder, sample_metadata
    ):
        view = builder.build_collapsed_view(sample_metadata)
        blocks = view["blocks"]

        # Find toggle block
        toggle_block = next(
            (b for b in blocks if b.get("block_id") == builder.STYLE_TOGGLE_BLOCK), None
        )
        assert toggle_block is not None
        assert toggle_block["type"] == "actions"
        assert toggle_block["elements"][0]["action_id"] == builder.STYLE_TOGGLE_ACTION
        assert toggle_block["elements"][0]["value"] == "expand"
        assert "Show Advanced" in toggle_block["elements"][0]["text"]["text"]

    def test_build_collapsed_view_stores_metadata(self, builder, sample_metadata):
        view = builder.build_collapsed_view(sample_metadata)
        metadata = json.loads(view["private_metadata"])
        assert metadata["message_text"] == sample_metadata["message_text"]
        assert metadata["user_id"] == sample_metadata["user_id"]
        assert metadata["show_advanced"] is False

    def test_build_expanded_view_returns_valid_modal(self, builder, sample_metadata):
        view = builder.build_expanded_view(sample_metadata)
        assert view["type"] == "modal"
        assert view["callback_id"] == "emoji_creation_modal"
        assert view["title"]["text"] == "Create Emoji"

    def test_build_expanded_view_contains_all_fields(self, builder, sample_metadata):
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        block_ids = [b.get("block_id") for b in blocks if b.get("block_id")]
        assert builder.DESCRIPTION_BLOCK in block_ids
        assert builder.EMOJI_NAME_BLOCK in block_ids
        assert builder.IMAGE_PROVIDER_BLOCK in block_ids
        assert builder.QUALITY_BLOCK in block_ids
        assert builder.BACKGROUND_BLOCK in block_ids
        assert builder.NUM_IMAGES_BLOCK in block_ids
        assert builder.STYLE_TEXT_BLOCK in block_ids
        assert builder.STYLE_TOGGLE_BLOCK in block_ids

    def test_build_expanded_view_toggle_collapses(self, builder, sample_metadata):
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        toggle_block = next(
            (b for b in blocks if b.get("block_id") == builder.STYLE_TOGGLE_BLOCK), None
        )
        assert toggle_block is not None
        assert toggle_block["elements"][0]["value"] == "collapse"
        assert "Hide Advanced" in toggle_block["elements"][0]["text"]["text"]

    def test_build_expanded_view_stores_metadata(self, builder, sample_metadata):
        view = builder.build_expanded_view(sample_metadata)
        metadata = json.loads(view["private_metadata"])
        assert metadata["message_text"] == sample_metadata["message_text"]
        assert metadata["show_advanced"] is True

    def test_build_expanded_view_emoji_name_is_optional(self, builder, sample_metadata):
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        name_block = next(
            (b for b in blocks if b.get("block_id") == builder.EMOJI_NAME_BLOCK), None
        )
        assert name_block is not None
        assert name_block.get("optional") is True

    def test_build_expanded_view_provider_default_is_openai_without_google(
        self, builder, sample_metadata
    ):
        """Provider should default to OpenAI when Google is not available."""
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        provider_block = next(
            (b for b in blocks if b.get("block_id") == builder.IMAGE_PROVIDER_BLOCK),
            None,
        )
        assert provider_block is not None
        initial_option = provider_block["element"]["initial_option"]
        assert initial_option["value"] == "openai"

    def test_build_expanded_view_provider_default_is_google_when_available(
        self, builder_with_google, sample_metadata
    ):
        """Provider should default to Google when available."""
        view = builder_with_google.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        provider_block = next(
            (
                b
                for b in blocks
                if b.get("block_id") == builder_with_google.IMAGE_PROVIDER_BLOCK
            ),
            None,
        )
        assert provider_block is not None
        initial_option = provider_block["element"]["initial_option"]
        assert initial_option["value"] == "google_gemini"

    def test_provider_options_without_google(self, builder, sample_metadata):
        """Only OpenAI option should be available when Google is not configured."""
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        provider_block = next(
            (b for b in blocks if b.get("block_id") == builder.IMAGE_PROVIDER_BLOCK),
            None,
        )
        options = provider_block["element"]["options"]
        assert len(options) == 1
        assert options[0]["value"] == "openai"

    def test_provider_options_with_google(self, builder_with_google, sample_metadata):
        """Both Google and OpenAI should be available when Google is configured."""
        view = builder_with_google.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        provider_block = next(
            (
                b
                for b in blocks
                if b.get("block_id") == builder_with_google.IMAGE_PROVIDER_BLOCK
            ),
            None,
        )
        options = provider_block["element"]["options"]
        assert len(options) == 2
        option_values = [o["value"] for o in options]
        assert "google_gemini" in option_values
        assert "openai" in option_values

    def test_build_expanded_view_quality_default_is_high(
        self, builder, sample_metadata
    ):
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        quality_block = next(
            (b for b in blocks if b.get("block_id") == builder.QUALITY_BLOCK), None
        )
        assert quality_block is not None
        initial_option = quality_block["element"]["initial_option"]
        assert initial_option["value"] == "high"

    def test_build_expanded_view_background_default_is_transparent(
        self, builder, sample_metadata
    ):
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        bg_block = next(
            (b for b in blocks if b.get("block_id") == builder.BACKGROUND_BLOCK), None
        )
        assert bg_block is not None
        initial_option = bg_block["element"]["initial_option"]
        assert initial_option["value"] == "transparent"

    def test_build_expanded_view_num_images_default_is_one(
        self, builder, sample_metadata
    ):
        view = builder.build_expanded_view(sample_metadata)
        blocks = view["blocks"]

        num_block = next(
            (b for b in blocks if b.get("block_id") == builder.NUM_IMAGES_BLOCK), None
        )
        assert num_block is not None
        initial_option = num_block["element"]["initial_option"]
        assert initial_option["value"] == "1"

    def test_modal_callback_id_constant(self, builder):
        assert builder.MODAL_CALLBACK_ID == "emoji_creation_modal"

    def test_block_ids_are_consistent(self, builder, sample_metadata):
        collapsed = builder.build_collapsed_view(sample_metadata)
        expanded = builder.build_expanded_view(sample_metadata)

        # Description block should have same ID in both views
        collapsed_desc = next(
            (
                b
                for b in collapsed["blocks"]
                if b.get("block_id") == builder.DESCRIPTION_BLOCK
            ),
            None,
        )
        expanded_desc = next(
            (
                b
                for b in expanded["blocks"]
                if b.get("block_id") == builder.DESCRIPTION_BLOCK
            ),
            None,
        )

        assert collapsed_desc is not None
        assert expanded_desc is not None
        assert (
            collapsed_desc["element"]["action_id"]
            == expanded_desc["element"]["action_id"]
        )
