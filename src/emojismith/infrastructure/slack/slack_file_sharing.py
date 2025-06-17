"""Slack file sharing repository implementation."""

import logging
from dataclasses import dataclass
from typing import Optional, Any, Dict
from io import BytesIO
from PIL import Image

from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

from emojismith.domain.entities.generated_emoji import GeneratedEmoji
from shared.domain.value_objects import (
    EmojiSharingPreferences,
    InstructionVisibility,
    ImageSize,
)

# Slack limits file uploads to 1–10 MB depending on plan; use safe lower bound.
MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024  # 8 MiB


@dataclass
class FileSharingResult:
    """Result of file sharing operation."""

    success: bool
    thread_ts: Optional[str] = None
    file_url: Optional[str] = None
    error: Optional[str] = None


class SlackFileSharingRepository:
    """Repository for sharing emoji files in Slack."""

    def __init__(self, slack_client: AsyncWebClient) -> None:
        self._client = slack_client
        self._logger = logging.getLogger(__name__)

    async def share_emoji_file(
        self,
        emoji: GeneratedEmoji,
        channel_id: str,
        preferences: EmojiSharingPreferences,
        requester_user_id: str,
        original_message_ts: Optional[str] = None,
    ) -> FileSharingResult:
        """Share emoji as a file with upload instructions."""
        try:
            # Try to join the channel first to avoid 'not_in_channel' errors
            await self._ensure_bot_in_channel(channel_id)
            # Prepare image data
            image_data = await self._prepare_image_data(emoji, preferences.image_size)

            # Early file-size validation to avoid wasted Slack API calls
            file_size = image_data.getbuffer().nbytes
            if file_size > MAX_FILE_SIZE_BYTES:
                self._logger.warning(
                    "Image size (%d bytes) exceeds Slack limit (%d bytes). "
                    "Aborting upload.",
                    file_size,
                    MAX_FILE_SIZE_BYTES,
                )
                return FileSharingResult(success=False, error="file_too_large")

            # Determine upload parameters based on share location
            upload_params: Dict[str, Any] = {
                "filename": f"{emoji.name}.png",
                "channels": [
                    channel_id
                ],  # files_upload_v2 expects a list of channel IDs
                "file": image_data,
                "title": f"Custom Emoji: :{emoji.name}:",
                "initial_comment": self._build_initial_comment(emoji.name, preferences),
            }

            # Handle thread-specific sharing
            thread_ts = None
            if preferences.thread_ts:
                # Share in existing thread
                thread_ts = preferences.thread_ts
                upload_params["thread_ts"] = thread_ts
            elif original_message_ts:
                # For new thread, we'll upload first then get the thread_ts
                upload_params["thread_ts"] = original_message_ts

            # Upload the file
            response = await self._client.files_upload_v2(**upload_params)

            if not response.get("ok"):
                return FileSharingResult(
                    success=False, error=response.get("error", "Unknown error")
                )

            file_info: Dict[str, Any] = response.get("file", {})
            file_url = file_info.get("url_private")

            # If creating new thread, get the timestamp from the file share
            if original_message_ts and not preferences.thread_ts:
                # For new threads, we need to post a message to create the thread
                # The file upload alone doesn't return a thread_ts
                message_response = await self._client.chat_postMessage(
                    channel=channel_id,
                    text=f"Generated custom emoji: :{emoji.name}:",
                    thread_ts=original_message_ts,
                )
                thread_ts = message_response.get("ts")

            # Post additional instructions if needed
            if preferences.include_upload_instructions:
                await self._post_instructions(
                    channel_id=channel_id,
                    thread_ts=thread_ts,
                    emoji_name=emoji.name,
                    preferences=preferences,
                    requester_user_id=requester_user_id,
                )

            return FileSharingResult(
                success=True,
                thread_ts=thread_ts,
                file_url=file_url,
            )

        except SlackApiError as e:
            self._logger.error(f"Slack API error sharing file: {e}")
            return FileSharingResult(
                success=False,
                error=str(e),
            )
        except Exception as e:
            self._logger.error(f"Unexpected error sharing file: {e}")
            return FileSharingResult(
                success=False,
                error=f"Unexpected error: {e}",
            )

    async def _prepare_image_data(
        self, emoji: GeneratedEmoji, image_size: ImageSize
    ) -> BytesIO:
        """Prepare image data for upload based on size preference."""
        if image_size == ImageSize.EMOJI_SIZE:
            # Resize to standard emoji size
            with Image.open(BytesIO(emoji.image_data)) as img:
                resized = img.resize((128, 128), Image.Resampling.LANCZOS)
                buf = BytesIO()
                resized.save(buf, format="PNG")
                buf.seek(0)
                return buf
        else:
            # Return full size image
            return BytesIO(emoji.image_data)

    def _build_initial_comment(
        self, emoji_name: str, preferences: EmojiSharingPreferences
    ) -> str:
        """Build the initial comment for the file upload."""
        comment = f"Generated custom emoji: :{emoji_name}:"

        if preferences.include_upload_instructions:
            comment += "\n\n*To add this emoji to your workspace:*"
            comment += "\n1. Right-click the image and save it"
            comment += "\n2. Go to Slack → Preferences → Emoji"
            comment += "\n3. Click 'Add Custom Emoji'"
            comment += f"\n4. Upload the image and name it `{emoji_name}`"
            comment += "\n5. Click 'Save'"
            comment += (
                f"\n\nThen you can use it by typing `:{emoji_name}:` in any message! 🎉"
            )

        return comment

    async def _post_instructions(
        self,
        channel_id: str,
        thread_ts: Optional[str],
        emoji_name: str,
        preferences: EmojiSharingPreferences,
        requester_user_id: str,
    ) -> None:
        """Post additional instructions based on visibility preferences."""
        # Instructions are already in the file comment for everyone visibility
        if preferences.instruction_visibility == InstructionVisibility.EVERYONE:
            return

        # For requester-only, send ephemeral message with instructions
        if preferences.instruction_visibility == InstructionVisibility.SUBMITTER_ONLY:
            instructions = self._build_upload_instructions(emoji_name)

            await self._client.chat_postEphemeral(
                channel=channel_id,
                user=requester_user_id,
                text=instructions,
                thread_ts=thread_ts,
            )

    def _build_upload_instructions(self, emoji_name: str) -> str:
        """Build detailed upload instructions."""
        return (
            f"*Your custom emoji `:{emoji_name}:` is ready!*\n\n"
            "To add it to the workspace:\n"
            "1. Download the image from the file above\n"
            "2. Go to Slack → Preferences → Emoji\n"
            "3. Click 'Add Custom Emoji'\n"
            f"4. Upload the image and name it `{emoji_name}`\n"
            "5. Click 'Save'\n\n"
            f"Then use it by typing `:{emoji_name}:` anywhere! 🚀"
        )

    async def _ensure_bot_in_channel(self, channel_id: str) -> None:
        """Ensure the bot is a member of the channel before uploading files."""
        try:
            # Try to join the channel - this will succeed if bot has permission
            # and the channel is public, or fail gracefully if already a member
            await self._client.conversations_join(channel=channel_id)
        except SlackApiError as e:
            error_code = e.response.get("error")

            # These errors are acceptable - bot is already in channel or has access
            if error_code in [
                "already_in_channel",
                "is_archived",
                "method_not_supported_for_channel_type",
            ]:
                return

            # For private channels, the bot needs to be invited manually
            if error_code in ["channel_not_found", "not_allowed", "restricted_action"]:
                self._logger.warning(
                    f"Bot cannot join channel {channel_id}: {error_code}. "
                    "Bot may need to be manually invited to private channels."
                )
                # Don't fail here - the file upload might still work if bot was
                # previously added
                return

            # For other errors, log but continue - the upload might still work
            self._logger.warning(f"Could not join channel {channel_id}: {error_code}")
        except Exception as e:
            # Log unexpected errors but don't fail the file sharing operation
            self._logger.warning(f"Unexpected error joining channel {channel_id}: {e}")
