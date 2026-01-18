"""Data Transfer Objects for shared domain concepts."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EmojiGenerationJobDto:
    """DTO for EmojiGenerationJob to decouple infrastructure from domain entities."""

    job_id: str
    user_description: str
    message_text: str
    user_id: str
    channel_id: str
    timestamp: str
    team_id: str
    emoji_name: str
    status: str
    sharing_preferences: dict[str, Any]
    created_at: str
    style_preferences: dict[str, Any] = field(default_factory=dict)
    generation_preferences: dict[str, Any] = field(default_factory=dict)
    trace_id: str = ""
    thread_ts: str | None = None
    image_provider: str = "google_gemini"
