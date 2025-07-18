"""Shared value objects for emoji generation domain."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ShareLocation(Enum):
    """Where to share the generated emoji."""

    ORIGINAL_CHANNEL = "channel"
    DIRECT_MESSAGE = "dm"
    NEW_THREAD = "new_thread"
    THREAD = "thread"

    @classmethod
    def from_form_value(cls, form_value: str) -> "ShareLocation":
        """Create from Slack form value."""
        mapping = {
            "channel": cls.ORIGINAL_CHANNEL,
            "dm": cls.DIRECT_MESSAGE,
            "new_thread": cls.NEW_THREAD,
            "thread": cls.THREAD,
        }
        return mapping.get(form_value, cls.ORIGINAL_CHANNEL)


class InstructionVisibility(Enum):
    """Visibility of emoji creation instructions."""

    EVERYONE = "EVERYONE"
    SUBMITTER_ONLY = "SUBMITTER_ONLY"

    @classmethod
    def from_form_value(cls, form_value: str) -> "InstructionVisibility":
        """Create from Slack form value."""
        mapping = {
            "visible": cls.EVERYONE,
            "hidden": cls.SUBMITTER_ONLY,
        }
        return mapping.get(form_value, cls.EVERYONE)


class ImageSize(Enum):
    """Image size for emoji generation."""

    EMOJI_SIZE = "EMOJI_SIZE"  # 512x512 - recommended
    SMALL = "SMALL"  # 256x256
    LARGE = "LARGE"  # 1024x1024

    @classmethod
    def from_form_value(cls, form_value: str) -> "ImageSize":
        """Create from Slack form value."""
        mapping = {
            "512x512": cls.EMOJI_SIZE,
            "256x256": cls.SMALL,
            "1024x1024": cls.LARGE,
        }
        return mapping.get(form_value, cls.EMOJI_SIZE)


class JobStatus(Enum):
    """Status of emoji generation job."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class EmojiSharingPreferences:
    """User preferences for emoji sharing and visibility."""

    share_location: ShareLocation
    instruction_visibility: InstructionVisibility
    image_size: ImageSize
    include_upload_instructions: bool = True
    thread_ts: str | None = None

    @classmethod
    def from_form_values(
        cls,
        share_location: str,
        instruction_visibility: str,
        image_size: str,
        thread_ts: str | None = None,
    ) -> "EmojiSharingPreferences":
        """Create from Slack form values."""
        return cls(
            share_location=ShareLocation.from_form_value(share_location),
            instruction_visibility=InstructionVisibility.from_form_value(
                instruction_visibility
            ),
            image_size=ImageSize.from_form_value(image_size),
            thread_ts=thread_ts,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "share_location": self.share_location.value,
            "instruction_visibility": self.instruction_visibility.value,
            "image_size": self.image_size.value,
            "include_upload_instructions": self.include_upload_instructions,
            "thread_ts": self.thread_ts,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EmojiSharingPreferences":
        """Create from dictionary."""
        return cls(
            share_location=ShareLocation(data["share_location"]),
            instruction_visibility=InstructionVisibility(
                data["instruction_visibility"]
            ),
            image_size=ImageSize(data["image_size"]),
            include_upload_instructions=data.get("include_upload_instructions", True),
            thread_ts=data.get("thread_ts"),
        )

    @classmethod
    def default_for_context(
        cls,
        context: str = "general",
        is_in_thread: bool = False,
        thread_ts: str | None = None,
    ) -> "EmojiSharingPreferences":
        """Create default preferences for a given context."""
        return cls(
            share_location=(
                ShareLocation.THREAD if is_in_thread else ShareLocation.ORIGINAL_CHANNEL
            ),
            instruction_visibility=InstructionVisibility.EVERYONE,
            image_size=ImageSize.EMOJI_SIZE,
            include_upload_instructions=True,
            thread_ts=thread_ts,
        )


class StyleType(Enum):
    CARTOON = "cartoon"
    REALISTIC = "realistic"
    MINIMALIST = "minimalist"
    PIXEL_ART = "pixel_art"

    @classmethod
    def from_form_value(cls, value: str) -> "StyleType":
        mapping = {
            "cartoon": cls.CARTOON,
            "realistic": cls.REALISTIC,
            "minimalist": cls.MINIMALIST,
            "pixel_art": cls.PIXEL_ART,
        }
        return mapping.get(value, cls.CARTOON)


class ColorScheme(Enum):
    BRIGHT = "bright"
    MUTED = "muted"
    MONOCHROME = "monochrome"
    AUTO = "auto"

    @classmethod
    def from_form_value(cls, value: str) -> "ColorScheme":
        mapping = {
            "bright": cls.BRIGHT,
            "muted": cls.MUTED,
            "monochrome": cls.MONOCHROME,
            "auto": cls.AUTO,
        }
        return mapping.get(value, cls.AUTO)


class DetailLevel(Enum):
    SIMPLE = "simple"
    DETAILED = "detailed"

    @classmethod
    def from_form_value(cls, value: str) -> "DetailLevel":
        mapping = {"simple": cls.SIMPLE, "detailed": cls.DETAILED}
        return mapping.get(value, cls.SIMPLE)


class Tone(Enum):
    FUN = "fun"
    NEUTRAL = "neutral"
    EXPRESSIVE = "expressive"

    @classmethod
    def from_form_value(cls, value: str) -> "Tone":
        mapping = {
            "fun": cls.FUN,
            "neutral": cls.NEUTRAL,
            "expressive": cls.EXPRESSIVE,
        }
        return mapping.get(value, cls.FUN)


@dataclass(frozen=True)
class EmojiStylePreferences:
    style_type: StyleType = StyleType.CARTOON
    color_scheme: ColorScheme = ColorScheme.AUTO
    detail_level: DetailLevel = DetailLevel.SIMPLE
    tone: Tone = Tone.FUN

    def to_prompt_fragment(self) -> str:
        """Generate natural language prompt fragment for AI."""
        parts = [f"in {self.style_type.value} style"]

        if self.color_scheme != ColorScheme.AUTO:
            color_text = (
                "bright and vibrant"
                if self.color_scheme == ColorScheme.BRIGHT
                else self.color_scheme.value
            )
            parts.append(f"with {color_text} colors")

        detail_text = (
            "clean and simple"
            if self.detail_level == DetailLevel.SIMPLE
            else "highly detailed"
        )
        parts.append(detail_text)

        tone_adjectives = {
            Tone.FUN: "playful and fun",
            Tone.NEUTRAL: "neutral and balanced",
            Tone.EXPRESSIVE: "expressive and dynamic",
        }
        parts.append(tone_adjectives.get(self.tone, "fun"))

        return ", ".join(parts)

    @classmethod
    def from_form_values(
        cls,
        style_type: str,
        color_scheme: str,
        detail_level: str,
        tone: str,
    ) -> "EmojiStylePreferences":
        return cls(
            style_type=StyleType.from_form_value(style_type),
            color_scheme=ColorScheme.from_form_value(color_scheme),
            detail_level=DetailLevel.from_form_value(detail_level),
            tone=Tone.from_form_value(tone),
        )

    def to_dict(self) -> dict[str, str]:
        return {
            "style_type": self.style_type.value,
            "color_scheme": self.color_scheme.value,
            "detail_level": self.detail_level.value,
            "tone": self.tone.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "EmojiStylePreferences":
        """Create from dictionary with validation."""
        import logging

        try:
            return cls(
                style_type=StyleType(data.get("style_type", "cartoon")),
                color_scheme=ColorScheme(data.get("color_scheme", "auto")),
                detail_level=DetailLevel(data.get("detail_level", "simple")),
                tone=Tone(data.get("tone", "fun")),
            )
        except (ValueError, KeyError) as e:
            logging.getLogger(__name__).warning(f"Invalid style preferences: {e}")
            return cls()  # Return safe defaults
