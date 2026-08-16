"""Slack modal builder for emoji creation.

Implements progressive disclosure for maximum capability with minimal friction.

NOTE: This module is in the application layer rather than presentation layer
because it defines the view-model structure used by the application handler.
The modal builder is tightly coupled to the webhook handler's form extraction logic.
"""

from __future__ import annotations

import json
from typing import Any

from emojismith.domain.value_objects.emoji_specification import (
    MAX_EMOJI_DESCRIPTION_LENGTH,
)


class EmojiCreationModalBuilder:
    """Builds Slack modal views with progressive disclosure.

    Simple mode: Just description input + generate button
    Advanced mode: Full control over model, quality, background, count, style
    """

    # Block IDs - must match extraction in submission handler
    DESCRIPTION_BLOCK = "emoji_description"
    EMOJI_NAME_BLOCK = "emoji_name"
    IMAGE_PROVIDER_BLOCK = "image_provider_block"
    QUALITY_BLOCK = "quality_block"
    BACKGROUND_BLOCK = "background_block"
    NUM_IMAGES_BLOCK = "num_images_block"
    STYLE_TEXT_BLOCK = "style_text_block"
    STYLE_TOGGLE_BLOCK = "style_toggle_block"

    # Action IDs - must match extraction in submission handler
    DESCRIPTION_ACTION = "description"
    NAME_ACTION = "name"
    PROVIDER_ACTION = "image_provider_select"
    QUALITY_ACTION = "quality_select"
    BACKGROUND_ACTION = "background_select"
    NUM_IMAGES_ACTION = "num_images_select"
    STYLE_TEXT_ACTION = "style_text_input"
    STYLE_TOGGLE_ACTION = "toggle_style_options"

    MODAL_CALLBACK_ID = "emoji_creation_modal"
    MAX_DESCRIPTION_LENGTH = MAX_EMOJI_DESCRIPTION_LENGTH
    MAX_EMOJI_NAME_LENGTH = 32

    def __init__(
        self,
        default_provider: str = "openai",
        google_available: bool = False,
    ) -> None:
        """Initialize modal builder with provider configuration.

        Args:
            default_provider: Default image provider ("openai" or "google_gemini")
            google_available: Whether Google API is configured and available
        """
        self._default_provider = default_provider
        self._google_available = google_available

    @property
    def default_provider(self) -> str:
        """Get the effective default image provider."""
        return self._get_effective_default_provider()

    def _get_provider_options(self) -> list[dict[str, Any]]:
        """Get available provider options based on configuration."""
        options = [
            {
                "text": {
                    "type": "plain_text",
                    "text": "🤖 GPT Image 2",
                },
                "value": "openai",
            },
        ]

        if self._google_available:
            options.insert(
                0,
                {
                    "text": {
                        "type": "plain_text",
                        "text": "🍌 Nano Banana Pro",
                    },
                    "value": "google_gemini",
                },
            )

        return options

    def _get_effective_default_provider(self) -> str:
        """Get the effective default provider based on availability."""
        if self._google_available and self._default_provider == "google_gemini":
            return "google_gemini"
        return "openai"

    def _get_image_provider_block(self) -> dict[str, Any]:
        """Get the image provider input block."""
        options = self._get_provider_options()
        default_provider = self._get_effective_default_provider()
        initial_option = next(
            (o for o in options if o["value"] == default_provider),
            options[0],
        )
        return {
            "type": "input",
            "block_id": self.IMAGE_PROVIDER_BLOCK,
            "optional": True,
            "element": {
                "type": "static_select",
                "action_id": self.PROVIDER_ACTION,
                "initial_option": initial_option,
                "options": options,
            },
            "label": {"type": "plain_text", "text": "Image Model"},
        }

    def build_collapsed_view(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Build simple mode modal (description only)."""
        metadata_with_state = {**metadata, "show_advanced": False}

        blocks = [
            # Description Input (main focus)
            {
                "type": "input",
                "block_id": self.DESCRIPTION_BLOCK,
                "element": {
                    "type": "plain_text_input",
                    "action_id": self.DESCRIPTION_ACTION,
                    "multiline": True,
                    "max_length": self.MAX_DESCRIPTION_LENGTH,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "A happy dancing banana wearing sunglasses...",
                    },
                },
                "label": {"type": "plain_text", "text": "Describe your emoji"},
            },
            # Image Provider (Basic Setting)
            self._get_image_provider_block(),
            # Toggle button
            {
                "type": "actions",
                "block_id": self.STYLE_TOGGLE_BLOCK,
                "elements": [
                    {
                        "type": "button",
                        "action_id": self.STYLE_TOGGLE_ACTION,
                        "text": {
                            "type": "plain_text",
                            "text": "▼ Show Advanced Options",
                            "emoji": True,
                        },
                        "value": "expand",
                    }
                ],
            },
        ]

        return {
            "type": "modal",
            "callback_id": self.MODAL_CALLBACK_ID,
            "title": {"type": "plain_text", "text": "Create Emoji"},
            "submit": {"type": "plain_text", "text": "✨ Generate"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": blocks,
            "private_metadata": json.dumps(metadata_with_state),
        }

    def build_expanded_view(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Build advanced mode modal (full options)."""
        metadata_with_state = {**metadata, "show_advanced": True}

        blocks = [
            # Description Input
            {
                "type": "input",
                "block_id": self.DESCRIPTION_BLOCK,
                "element": {
                    "type": "plain_text_input",
                    "action_id": self.DESCRIPTION_ACTION,
                    "multiline": True,
                    "max_length": self.MAX_DESCRIPTION_LENGTH,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "A happy dancing banana wearing sunglasses...",
                    },
                },
                "label": {"type": "plain_text", "text": "Describe your emoji"},
            },
            # Image Provider (Basic Setting)
            self._get_image_provider_block(),
            # Emoji Name (optional)
            {
                "type": "input",
                "block_id": self.EMOJI_NAME_BLOCK,
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": self.NAME_ACTION,
                    "max_length": self.MAX_EMOJI_NAME_LENGTH,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "e.g., dancing_banana (auto-generated if empty)",
                    },
                },
                "label": {"type": "plain_text", "text": "Emoji Name"},
                "hint": {
                    "type": "plain_text",
                    "text": (
                        "Will become :emoji_name: (lowercase letters, numbers, "
                        "and underscores)"
                    ),
                },
            },
            {"type": "divider"},
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": "⚙️ *Advanced Options*"}],
            },
            # Quality maps to native rendering quality or output resolution.
            {
                "type": "input",
                "block_id": self.QUALITY_BLOCK,
                "optional": True,
                "element": {
                    "type": "static_select",
                    "action_id": self.QUALITY_ACTION,
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": "✨ High (best quality)",
                        },
                        "value": "high",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "✨ High (best quality)",
                            },
                            "value": "high",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "⚖️ Medium (balanced)",
                            },
                            "value": "medium",
                        },
                        {
                            "text": {"type": "plain_text", "text": "⚡ Low (fastest)"},
                            "value": "low",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Output Quality"},
            },
            # Background
            {
                "type": "input",
                "block_id": self.BACKGROUND_BLOCK,
                "optional": True,
                "element": {
                    "type": "static_select",
                    "action_id": self.BACKGROUND_ACTION,
                    "initial_option": {
                        "text": {
                            "type": "plain_text",
                            "text": "✂️ Clean cutout (best effort)",
                        },
                        "value": "transparent",
                    },
                    "options": [
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "✂️ Clean cutout (best effort)",
                            },
                            "value": "transparent",
                        },
                        {
                            "text": {"type": "plain_text", "text": "🎨 Auto"},
                            "value": "auto",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Background"},
                "hint": {
                    "type": "plain_text",
                    "text": (
                        "Models may return a solid background; a clean cutout is "
                        "prompt guidance and is not guaranteed."
                    ),
                },
            },
            # Number of Images
            {
                "type": "input",
                "block_id": self.NUM_IMAGES_BLOCK,
                "optional": True,
                "element": {
                    "type": "static_select",
                    "action_id": self.NUM_IMAGES_ACTION,
                    "initial_option": {
                        "text": {"type": "plain_text", "text": "1 image"},
                        "value": "1",
                    },
                    "options": [
                        {
                            "text": {"type": "plain_text", "text": "1 image"},
                            "value": "1",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "2 images (choose best)",
                            },
                            "value": "2",
                        },
                        {
                            "text": {
                                "type": "plain_text",
                                "text": "4 images (choose best)",
                            },
                            "value": "4",
                        },
                    ],
                },
                "label": {"type": "plain_text", "text": "Number of Options"},
            },
            # Style Text (free-form)
            {
                "type": "input",
                "block_id": self.STYLE_TEXT_BLOCK,
                "optional": True,
                "element": {
                    "type": "plain_text_input",
                    "action_id": self.STYLE_TEXT_ACTION,
                    "placeholder": {
                        "type": "plain_text",
                        "text": "cartoon, pixel art, minimalist, 3D, watercolor...",
                    },
                },
                "label": {"type": "plain_text", "text": "Style"},
            },
            # Toggle button
            {
                "type": "actions",
                "block_id": self.STYLE_TOGGLE_BLOCK,
                "elements": [
                    {
                        "type": "button",
                        "action_id": self.STYLE_TOGGLE_ACTION,
                        "text": {
                            "type": "plain_text",
                            "text": "▲ Hide Advanced Options",
                            "emoji": True,
                        },
                        "value": "collapse",
                    }
                ],
            },
        ]

        return {
            "type": "modal",
            "callback_id": self.MODAL_CALLBACK_ID,
            "title": {"type": "plain_text", "text": "Create Emoji"},
            "submit": {"type": "plain_text", "text": "✨ Generate"},
            "close": {"type": "plain_text", "text": "Cancel"},
            "blocks": blocks,
            "private_metadata": json.dumps(metadata_with_state),
        }
