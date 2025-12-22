"""Tests for ImageProvider value object."""


from emojismith.domain.value_objects.image_provider import ImageProvider


class TestImageProviderFromString:
    """Tests for ImageProvider.from_string method."""

    def test_from_string_when_openai_value_returns_openai_provider(self):
        """Test that 'openai' string returns OPENAI provider."""
        result = ImageProvider.from_string("openai")
        assert result == ImageProvider.OPENAI

    def test_from_string_when_google_gemini_value_returns_gemini_provider(self):
        """Test that 'google_gemini' string returns GOOGLE_GEMINI provider."""
        result = ImageProvider.from_string("google_gemini")
        assert result == ImageProvider.GOOGLE_GEMINI

    def test_from_string_when_invalid_value_returns_openai_default(self):
        """Test that invalid values default to OPENAI provider."""
        result = ImageProvider.from_string("invalid_provider")
        assert result == ImageProvider.OPENAI

    def test_from_string_when_uppercase_value_is_case_insensitive(self):
        """Test that from_string is case insensitive."""
        result = ImageProvider.from_string("OPENAI")
        assert result == ImageProvider.OPENAI

        result = ImageProvider.from_string("GOOGLE_GEMINI")
        assert result == ImageProvider.GOOGLE_GEMINI

    def test_from_string_when_mixed_case_value_is_case_insensitive(self):
        """Test that from_string handles mixed case."""
        result = ImageProvider.from_string("OpenAI")
        assert result == ImageProvider.OPENAI

        result = ImageProvider.from_string("Google_Gemini")
        assert result == ImageProvider.GOOGLE_GEMINI

    def test_from_string_when_empty_string_returns_openai_default(self):
        """Test that empty string defaults to OPENAI provider."""
        result = ImageProvider.from_string("")
        assert result == ImageProvider.OPENAI


class TestImageProviderValues:
    """Tests for ImageProvider enum values."""

    def test_openai_value_is_openai(self):
        """Test that OPENAI enum has correct value."""
        assert ImageProvider.OPENAI.value == "openai"

    def test_google_gemini_value_is_google_gemini(self):
        """Test that GOOGLE_GEMINI enum has correct value."""
        assert ImageProvider.GOOGLE_GEMINI.value == "google_gemini"

    def test_enum_values_usable_as_strings(self):
        """Test that ImageProvider values can be used as strings via .value."""
        assert ImageProvider.OPENAI.value == "openai"
        assert ImageProvider.GOOGLE_GEMINI.value == "google_gemini"
        # Values work with string operations
        assert f"provider:{ImageProvider.OPENAI.value}" == "provider:openai"
