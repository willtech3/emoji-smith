"""Slack payload models for webhook package."""

from dataclasses import dataclass
from typing import Dict, Any, Optional


@dataclass
class SlackUser:
    """Slack user information."""

    id: str
    name: str
    username: Optional[str] = None
    team_id: Optional[str] = None


@dataclass
class SlackChannel:
    """Slack channel information."""

    id: str
    name: Optional[str] = None


@dataclass
class SlackTeam:
    """Slack team information."""

    id: str
    domain: Optional[str] = None


@dataclass
class SlackMessage:
    """Slack message information."""

    text: str
    ts: str
    user: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SlackMessage":
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
    def from_dict(cls, data: Dict[str, Any]) -> "MessageActionPayload":
        """Create from dictionary."""
        return cls(
            type=data["type"],
            callback_id=data["callback_id"],
            trigger_id=data["trigger_id"],
            user=SlackUser(**data["user"]),
            channel=SlackChannel(
                id=data["channel"]["id"], name=data["channel"].get("name")
            ),
            message=SlackMessage.from_dict(data["message"]),
            team=SlackTeam(**data["team"]),
        )


@dataclass
class FormElement:
    """Slack form element."""

    value: str


@dataclass
class FormSelect:
    """Slack form select element."""

    selected_option: Dict[str, str]

    def __getitem__(self, key: str) -> Any:
        """Allow dict-like access for compatibility."""
        if key == "selected_option":
            return self.selected_option
        raise KeyError(key)


@dataclass
class FormBlock:
    """Slack form block."""

    description: Optional[FormElement] = None
    share_location_select: Optional[FormSelect] = None
    visibility_select: Optional[FormSelect] = None
    size_select: Optional[FormSelect] = None


@dataclass
class FormValues:
    """Slack form values."""

    emoji_description: FormBlock
    share_location: FormBlock
    instruction_visibility: FormBlock
    image_size: FormBlock

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
    def from_dict(cls, data: Dict[str, Any]) -> "ModalSubmissionPayload":
        """Create from dictionary."""
        view_data = data["view"]
        state_data = view_data["state"]
        values_data = state_data["values"]

        # Create form blocks with proper handling of optional fields
        def create_form_block(block_data: Dict[str, Any]) -> FormBlock:
            block = FormBlock()
            if "description" in block_data:
                block.description = FormElement(
                    value=block_data["description"]["value"]
                )
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
            return block

        form_values = FormValues(
            emoji_description=create_form_block(values_data["emoji_description"]),
            share_location=create_form_block(values_data["share_location"]),
            instruction_visibility=create_form_block(
                values_data["instruction_visibility"]
            ),
            image_size=create_form_block(values_data["image_size"]),
        )

        view = ModalView(
            callback_id=view_data["callback_id"],
            state=FormState(values=form_values),
            private_metadata=view_data["private_metadata"],
        )

        return cls(type=data["type"], view=view)
