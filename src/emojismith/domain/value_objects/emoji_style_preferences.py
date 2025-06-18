from dataclasses import dataclass
from enum import Enum


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
        parts = [f"in {self.style_type.value} style"]
        if self.color_scheme != ColorScheme.AUTO:
            parts.append(f"with {self.color_scheme.value} colors")
        parts.append(f"{self.detail_level.value} detail")
        parts.append(f"{self.tone.value} tone")
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
        return cls(
            style_type=StyleType(data.get("style_type", "cartoon")),
            color_scheme=ColorScheme(data.get("color_scheme", "auto")),
            detail_level=DetailLevel(data.get("detail_level", "simple")),
            tone=Tone(data.get("tone", "fun")),
        )
