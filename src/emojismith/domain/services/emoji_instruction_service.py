"""Service for generating user instructions for emoji uploads."""

from shared.domain.value_objects import EmojiSharingPreferences


class EmojiInstructionService:
    """Service to build user guidance messages for emoji usage."""

    def build_emoji_upload_steps(self, emoji_name: str) -> str:
        """Build the step-by-step emoji upload instructions."""
        return (
            "1. Right-click the image and save it\n"
            "2. Click the smiley icon in the message box\n"
            "3. Select 'Add emoji'\n"
            f"4. Upload the image and name it `{emoji_name}` (name shown above)\n"
            "5. Click 'Add'"
        )

    def build_initial_comment(
        self, emoji_name: str, preferences: EmojiSharingPreferences
    ) -> str:
        """Build the initial comment for the file upload."""
        comment = f"Generated custom emoji: :{emoji_name}:"

        if preferences.include_upload_instructions:
            comment += "\n\n*To add this emoji to your workspace:*\n"
            comment += self.build_emoji_upload_steps(emoji_name)
            comment += (
                f"\n\nThen you can use it by typing `:{emoji_name}:` in any message! "
                "If you generated multiple variations, repeat these steps "
                "for each file (each file shows its own emoji name)."
            )

        return comment

    def build_upload_instructions(self, emoji_name: str) -> str:
        """Build detailed upload instructions (typically for ephemeral messages)."""
        return (
            f"*Your custom emoji `:{emoji_name}:` is ready!*\n\n"
            "To add it to the workspace:\n"
            f"{self.build_emoji_upload_steps(emoji_name)}\n\n"
            f"Then use it by typing `:{emoji_name}:` anywhere! 🚀"
        )
