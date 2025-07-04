"""Slack payload models for webhook package."""

from dataclasses import dataclass
from typing import Any


@dataclass
class SlackUser:
    """Slack user information."""

    id: str
    name: str = ""  # Make name optional with default
    username: str | None = None
    team_id: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlackUser":
        """Create from dictionary, ignoring extra fields."""
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            username=data.get("username"),
            team_id=data.get("team_id"),
        )


@dataclass
class SlackChannel:
    """Slack channel information."""

    id: str
    name: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlackChannel":
        """Create from dictionary, ignoring extra fields."""
        return cls(id=data["id"], name=data.get("name"))


@dataclass
class SlackTeam:
    """Slack team information."""

    id: str
    domain: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlackTeam":
        """Create from dictionary, ignoring extra fields."""
        return cls(id=data["id"], domain=data.get("domain"))


@dataclass
class SlackMessage:
    """Slack message information."""

    text: str
    ts: str
    user: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SlackMessage":
        """Create from dictionary, ignoring extra fields."""
        return cls(text=data["text"], ts=data["ts"], user=data["user"])


@dataclass
class MessageActionPayload:
    """Represents a Slack message action payload."""

    type: str
    callback_id: str
    trigger_id: str
    user: SlackUser
    channel: SlackChannel
    message: SlackMessage
    team: SlackTeam

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MessageActionPayload":
        """Create from dictionary."""
        return cls(
            type=data["type"],
            callback_id=data["callback_id"],
            trigger_id=data["trigger_id"],
            user=SlackUser.from_dict(data["user"]),
            channel=SlackChannel.from_dict(data["channel"]),
            message=SlackMessage.from_dict(data["message"]),
            team=SlackTeam.from_dict(data["team"]),
        )


@dataclass
class FormElement:
    """Slack form element."""

    value: str


@dataclass
class FormSelect:
    """Slack form select element."""

    selected_option: dict[str, str]

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for compatibility."""
        if key == "selected_option":
            return self.selected_option
        raise KeyError(key)


@dataclass
class FormBlock:
    """Slack form block."""

    description: FormElement | None = None
    name: FormElement | None = None
    share_location_select: FormSelect | None = None
    visibility_select: FormSelect | None = None
    size_select: FormSelect | None = None
    style_select: FormSelect | None = None
    color_select: FormSelect | None = None
    detail_select: FormSelect | None = None
    tone_select: FormSelect | None = None


@dataclass
class FormValues:
    """Slack form values."""

    emoji_name: FormBlock
    emoji_description: FormBlock
    share_location: FormBlock
    instruction_visibility: FormBlock
    image_size: FormBlock
    style_preferences: FormBlock
    color_scheme: FormBlock
    tone: FormBlock

    def __getitem__(self, key: str) -> FormBlock:
        """Allow dict-like access for compatibility."""
        attr_name = key.replace("-", "_")
        result = getattr(self, attr_name)
        if not isinstance(result, FormBlock):
            raise KeyError(f"Invalid form block key: {key}")
        return result


@dataclass
class FormState:
    """Slack form state."""

    values: FormValues


@dataclass
class ModalView:
    """Slack modal view."""

    callback_id: str
    state: FormState
    private_metadata: str


@dataclass
class ModalSubmissionPayload:
    """Represents a Slack modal submission payload."""

    type: str
    view: ModalView

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ModalSubmissionPayload":
        """Create from dictionary."""
        view_data = data["view"]
        state_data = view_data["state"]
        values_data = state_data["values"]

        # Create form blocks with proper handling of optional fields
        def create_form_block(block_data: dict[str, Any]) -> FormBlock:
            block = FormBlock()
            if "description" in block_data:
                block.description = FormElement(
                    value=block_data["description"]["value"]
                )
            if "name" in block_data:
                block.name = FormElement(value=block_data["name"]["value"])
            if "share_location_select" in block_data:
                block.share_location_select = FormSelect(
                    selected_option=block_data["share_location_select"][
                        "selected_option"
                    ]
                )
            if "visibility_select" in block_data:
                block.visibility_select = FormSelect(
                    selected_option=block_data["visibility_select"]["selected_option"]
                )
            if "size_select" in block_data:
                block.size_select = FormSelect(
                    selected_option=block_data["size_select"]["selected_option"]
                )
            if "style_select" in block_data:
                block.style_select = FormSelect(
                    selected_option=block_data["style_select"]["selected_option"]
                )
            if "color_select" in block_data:
                block.color_select = FormSelect(
                    selected_option=block_data["color_select"]["selected_option"]
                )
            if "detail_select" in block_data:
                block.detail_select = FormSelect(
                    selected_option=block_data["detail_select"]["selected_option"]
                )
            if "tone_select" in block_data:
                block.tone_select = FormSelect(
                    selected_option=block_data["tone_select"]["selected_option"]
                )
            return block

        form_values = FormValues(
            emoji_name=create_form_block(values_data["emoji_name"]),
            emoji_description=create_form_block(values_data["emoji_description"]),
            share_location=create_form_block(values_data.get("share_location", {})),
            instruction_visibility=create_form_block(
                values_data.get("instruction_visibility", {})
            ),
            image_size=create_form_block(values_data.get("image_size", {})),
            style_preferences=create_form_block(
                values_data.get("style_preferences", {})
            ),
            color_scheme=create_form_block(values_data.get("color_scheme", {})),
            tone=create_form_block(values_data.get("tone", {})),
        )

        view = ModalView(
            callback_id=view_data["callback_id"],
            state=FormState(values=form_values),
            private_metadata=view_data["private_metadata"],
        )

        return cls(type=data["type"], view=view)
