"""Service for parsing and extracting context from Slack messages."""

import re
from typing import Any, Protocol


class SlackClientProtocol(Protocol):
    """Protocol for Slack client interface."""

    def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information from Slack API."""
        ...


class CodeLanguageDetector:
    """Detect programming language from code snippets."""

    def detect(self, code: str) -> str:
        """Detect the programming language from a code snippet.

        Args:
            code: The code snippet to analyze

        Returns:
            The detected language name or "code" if unknown
        """
        code_lower = code.lower()

        # Python detection
        if any(
            keyword in code_lower for keyword in ["def ", "import ", "print(", "python"]
        ):
            return "Python"

        # JavaScript detection
        if any(
            keyword in code_lower
            for keyword in ["function ", "console.log", "const ", "let ", "var "]
        ):
            return "JavaScript"

        # Java detection
        if any(
            keyword in code_lower
            for keyword in ["public class", "public static", "system.out.println"]
        ):
            return "Java"

        # SQL detection
        if any(
            keyword in code_lower
            for keyword in ["select ", "from ", "where ", "insert ", "update "]
        ):
            return "SQL"

        # Default fallback
        return "code"


class SlackMessageParser:
    """Parse Slack messages to extract clean context for AI processing."""

    def __init__(self, slack_client: SlackClientProtocol) -> None:
        """Initialize the parser with a Slack client.

        Args:
            slack_client: Client for accessing Slack API
        """
        self.slack_client = slack_client
        self.code_language_detector = CodeLanguageDetector()

    def extract_clean_context(self, slack_message: str, team_id: str) -> dict[str, Any]:
        """Extract clean context from a Slack message.

        Args:
            slack_message: The raw Slack message text
            team_id: The Slack team ID for user lookups

        Returns:
            Dictionary containing:
                - clean_text: Message with mentions replaced and formatting removed
                - mentions: List of mentioned user names
                - code_context: Description of code content if present
                - sentiment: Detected sentiment (positive/negative/neutral)
                - existing_emoji: List of emoji names already in the message
        """
        result: dict[str, Any] = {
            "clean_text": "",
            "mentions": [],
            "code_context": None,
            "sentiment": None,
            "existing_emoji": [],
        }

        # Handle empty messages
        if not slack_message:
            result["sentiment"] = "neutral"
            return result

        # Work with a copy to preserve original
        processed_message = slack_message

        # Extract and replace mentions with readable names
        mention_pattern = re.compile(r"<@(U[A-Z0-9]+)>")
        mentions = mention_pattern.findall(processed_message)
        for user_id in mentions:
            user_info = self.slack_client.get_user_info(user_id)
            readable_name = user_info.get("real_name", "Unknown User")
            processed_message = processed_message.replace(
                f"<@{user_id}>", readable_name
            )
            result["mentions"].append(readable_name)

        # Handle code blocks
        code_block_pattern = re.compile(r"```(.*?)```", re.DOTALL)
        code_blocks = code_block_pattern.findall(processed_message)
        if code_blocks:
            # Analyze first code block for language
            language = self.code_language_detector.detect(code_blocks[0])
            result["code_context"] = f"about {language} code"
            # Remove code blocks from message
            processed_message = code_block_pattern.sub("", processed_message)

        # Extract existing emoji
        emoji_pattern = re.compile(r":([a-zA-Z0-9_]+):")
        existing_emoji = emoji_pattern.findall(processed_message)
        result["existing_emoji"] = existing_emoji

        # Clean URLs but note their presence
        url_pattern = re.compile(r"<https?://[^\s|>]+(?:\|([^>]+))?>")
        processed_message = url_pattern.sub(
            lambda m: m.group(1) or "[link]", processed_message
        )

        # Remove Slack formatting characters
        formatting_chars = ["*", "_", "~", "`"]
        for char in formatting_chars:
            processed_message = processed_message.replace(char, "")

        # Clean up whitespace
        processed_message = " ".join(processed_message.split())
        result["clean_text"] = processed_message.strip()

        # Analyze sentiment
        result["sentiment"] = self._analyze_sentiment(processed_message)

        return result

    def _analyze_sentiment(self, text: str) -> str:
        """Analyze sentiment of the text.

        Args:
            text: The text to analyze

        Returns:
            "positive", "negative", or "neutral"
        """
        # Simple keyword-based sentiment analysis
        positive_words = [
            "awesome",
            "great",
            "excellent",
            "happy",
            "celebrate",
            "success",
            "wonderful",
            "fantastic",
            "amazing",
            "good",
            "nice",
            "love",
            "perfect",
            "brilliant",
            "outstanding",
            "superb",
            "complete",
            "done",
        ]
        negative_words = [
            "bug",
            "error",
            "failed",
            "broken",
            "issue",
            "problem",
            "wrong",
            "bad",
            "terrible",
            "awful",
            "horrible",
            "critical",
            "crash",
            "down",
            "slow",
            "stuck",
            "blocked",
            "urgent",
        ]

        text_lower = text.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"
