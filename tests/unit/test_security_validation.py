"""Security tests for input validation and injection attack prevention."""

import pytest

from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from emojismith.domain.exceptions import ValidationError


class TestSecurityValidation:
    """Test security aspects including input validation and injection prevention."""

    # Path Traversal Tests
    @pytest.mark.parametrize(
        "path_traversal_input",
        [
            "../../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "....//....//....//etc/passwd",
            "..;/..;/..;/etc/passwd",
        ],
    )
    def test_path_traversal_prevention(self, path_traversal_input):
        """Test that path traversal attempts are blocked."""
        # Create emoji specification with malicious path
        with pytest.raises(ValidationError) as exc_info:
            EmojiSpecification(
                description=path_traversal_input,
                context="test",
            )
        assert "path traversal" in str(exc_info.value)

    # Environment Variable Injection Tests
    @pytest.mark.parametrize(
        "env_injection",
        [
            "${OPENAI_API_KEY}",
            "$SLACK_BOT_TOKEN",
            "$(printenv)",
            "`echo $AWS_SECRET_ACCESS_KEY`",
        ],
    )
    def test_environment_variable_injection_prevention(self, env_injection):
        """Test that environment variable injection is prevented."""
        # Create specification with env var injection attempt
        spec = EmojiSpecification(
            description=env_injection,
            context="test",
        )

        # The injection attempt should be treated as literal text
        assert spec.description == env_injection
        assert "$" in spec.description or "`" in spec.description

    # Helper Methods
    def _create_modal_values(
        self, emoji_name="test_emoji", emoji_description="test description"
    ):
        """Create modal form values for testing."""
        return {
            "emoji_name": {"name": {"value": emoji_name}},
            "emoji_description": {"description": {"value": emoji_description}},
            "share_location": {
                "share_location_select": {"selected_option": {"value": "channel"}}
            },
            "instruction_visibility": {
                "visibility_select": {"selected_option": {"value": "visible"}}
            },
            "image_size": {"size_select": {"selected_option": {"value": "512x512"}}},
            "style_type": {"style_select": {"selected_option": {"value": "cartoon"}}},
            "color_scheme": {"color_select": {"selected_option": {"value": "auto"}}},
            "detail_level": {"detail_select": {"selected_option": {"value": "simple"}}},
            "tone": {"tone_select": {"selected_option": {"value": "fun"}}},
        }
