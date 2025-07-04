"""Tests for SlackMessageParser service."""

import pytest

from emojismith.domain.services.slack_message_parser import (
    CodeLanguageDetector,
    SlackMessageParser,
)


class MockSlackClient:
    """Mock Slack client for testing."""

    def __init__(self):
        self.user_map = {
            "U123456": {"real_name": "Alice Johnson"},
            "U789012": {"real_name": "Bob Smith"},
        }

    def get_user_info(self, user_id: str) -> dict:
        """Get mock user info."""
        return self.user_map.get(user_id, {"real_name": "Unknown User"})


class TestCodeLanguageDetector:
    """Test the code language detector."""

    def test_code_language_detector_with_python_code_returns_python(self):
        """Test detecting Python code."""
        detector = CodeLanguageDetector()
        python_code = 'def hello():\n    print("Hello World")'
        assert detector.detect(python_code) == "Python"

    def test_code_language_detector_with_javascript_code_returns_javascript(self):
        """Test detecting JavaScript code."""
        detector = CodeLanguageDetector()
        js_code = 'function hello() {\n    console.log("Hello World");\n}'
        assert detector.detect(js_code) == "JavaScript"

    def test_code_language_detector_with_java_code_returns_java(self):
        """Test detecting Java code."""
        detector = CodeLanguageDetector()
        java_code = (
            "public class Hello {\n"
            "    public static void main(String[] args) {\n"
            '        System.out.println("Hello");\n'
            "    }\n}"
        )
        assert detector.detect(java_code) == "Java"

    def test_code_language_detector_with_sql_query_returns_sql(self):
        """Test detecting SQL code."""
        detector = CodeLanguageDetector()
        sql_code = "SELECT * FROM users WHERE active = true"
        assert detector.detect(sql_code) == "SQL"

    def test_code_language_detector_with_unknown_text_returns_code(self):
        """Test detecting unknown code."""
        detector = CodeLanguageDetector()
        unknown_code = "Some random text that isn't code"
        assert detector.detect(unknown_code) == "code"


class TestSlackMessageParser:
    """Test the Slack message parser."""

    @pytest.fixture()
    def parser(self):
        """Create a parser with mock Slack client."""
        return SlackMessageParser(MockSlackClient())

    def test_slack_message_parser_with_simple_text_returns_clean(self, parser):
        """Test parsing a simple message without special formatting."""
        result = parser.extract_clean_context("Hello world!", "T123")
        assert result["clean_text"] == "Hello world!"
        assert result["mentions"] == []
        assert result["code_context"] is None
        assert result["existing_emoji"] == []
        assert result["sentiment"] == "neutral"

    def test_slack_message_parser_with_mentions_converts_to_names(self, parser):
        """Test parsing mentions and converting to readable names."""
        message = "Hey <@U123456>, can you review <@U789012>'s PR?"
        result = parser.extract_clean_context(message, "T123")
        assert (
            result["clean_text"] == "Hey Alice Johnson, can you review Bob Smith's PR?"
        )
        assert result["mentions"] == ["Alice Johnson", "Bob Smith"]

    def test_slack_message_parser_with_unknown_user_returns_default(self, parser):
        """Test parsing unknown user mention."""
        message = "Thanks <@U999999> for the help!"
        result = parser.extract_clean_context(message, "T123")
        assert result["clean_text"] == "Thanks Unknown User for the help!"
        assert result["mentions"] == ["Unknown User"]

    def test_slack_message_parser_with_code_blocks_extracts_language(self, parser):
        """Test parsing code blocks."""
        message = 'Here is the fix:\n```def fix_bug():\n    return "fixed"```'
        result = parser.extract_clean_context(message, "T123")
        assert result["code_context"] == "about Python code"
        assert "```" not in result["clean_text"]

    def test_slack_message_parser_with_multiple_blocks_uses_first(self, parser):
        """Test parsing multiple code blocks (only first is detected)."""
        message = (
            "First:\n```python\nprint('hi')\n```\nSecond:\n```js\nconsole.log('hi')```"
        )
        result = parser.extract_clean_context(message, "T123")
        assert result["code_context"] == "about Python code"

    def test_slack_message_parser_with_emoji_extracts_names(self, parser):
        """Test extracting existing emoji from message."""
        message = "Great job :clap: :rocket: Let's :celebrate: this!"
        result = parser.extract_clean_context(message, "T123")
        assert result["existing_emoji"] == ["clap", "rocket", "celebrate"]

    def test_slack_message_parser_with_urls_replaces_with_text(self, parser):
        """Test parsing URLs."""
        message = (
            "Check out <https://example.com|our website> and <https://docs.example.com>"
        )
        result = parser.extract_clean_context(message, "T123")
        assert result["clean_text"] == "Check out our website and [link]"

    def test_slack_message_parser_with_formatting_removes_characters(self, parser):
        """Test removing Slack formatting characters."""
        message = "This is *bold* and _italic_ and ~strikethrough~ and `code`"
        result = parser.extract_clean_context(message, "T123")
        assert (
            result["clean_text"] == "This is bold and italic and strikethrough and code"
        )

    def test_slack_message_parser_with_positive_words_returns_positive(self, parser):
        """Test detecting positive sentiment."""
        message = (
            "Awesome work team! Great success on the launch. Excellent job everyone!"
        )
        result = parser.extract_clean_context(message, "T123")
        assert result["sentiment"] == "positive"

    def test_slack_message_parser_with_negative_words_returns_negative(self, parser):
        """Test detecting negative sentiment."""
        message = (
            "Found a critical bug that's broken the build. "
            "Major issue with deployment failed."
        )
        result = parser.extract_clean_context(message, "T123")
        assert result["sentiment"] == "negative"

    def test_slack_message_parser_with_neutral_text_returns_neutral(self, parser):
        """Test detecting neutral sentiment."""
        message = "The meeting is scheduled for tomorrow at 3pm"
        result = parser.extract_clean_context(message, "T123")
        assert result["sentiment"] == "neutral"

    def test_slack_message_parser_with_complex_message_parses_all(self, parser):
        """Test parsing a complex message with multiple elements."""
        message = (
            "Hey <@U123456>, the *deployment* is complete! :rocket: "
            "Check the logs at <https://logs.example.com|dashboard>. "
            "```python\nif success:\n    celebrate()```"
            "Great work on fixing that bug :bug: :fixed:"
        )
        result = parser.extract_clean_context(message, "T123")

        assert "Alice Johnson" in result["clean_text"]
        assert result["mentions"] == ["Alice Johnson"]
        assert result["code_context"] == "about Python code"
        assert result["existing_emoji"] == ["rocket", "bug", "fixed"]
        assert result["sentiment"] == "positive"
        assert "[link]" in result["clean_text"] or "dashboard" in result["clean_text"]
        assert "deployment is complete!" in result["clean_text"]

    def test_slack_message_parser_with_empty_message_returns_empty(self, parser):
        """Test parsing empty message."""
        result = parser.extract_clean_context("", "T123")
        assert result["clean_text"] == ""
        assert result["mentions"] == []
        assert result["code_context"] is None
        assert result["existing_emoji"] == []
        assert result["sentiment"] == "neutral"

    def test_slack_message_parser_with_whitespace_only_returns_empty(self, parser):
        """Test parsing whitespace-only message."""
        result = parser.extract_clean_context("   \n\t  ", "T123")
        assert result["clean_text"] == ""
        assert result["sentiment"] == "neutral"
