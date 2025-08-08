"""Service for building contextual prompts for emoji generation."""

from emojismith.domain.value_objects.emoji_specification import EmojiSpecification


class PromptBuilderService:
    """Build optimized prompts by analyzing context and merging with descriptions."""

    def __init__(
        self,
        max_prompt_length: int = 150,
        style_modifiers: dict[str, str] | None = None,
    ) -> None:
        """Initialize the service with configuration.

        Args:
            max_prompt_length: Maximum length for generated prompts
            style_modifiers: Custom style modifier templates
        """
        self.max_prompt_length = max_prompt_length
        self.style_modifiers = style_modifiers or self._default_style_modifiers()

    def _default_style_modifiers(self) -> dict[str, str]:
        """Provide default style modifiers."""
        return {
            "cartoon": (
                "in a vibrant, colorful cartoon style with "
                "playful and exaggerated features"
            ),
            "minimalist": (
                "in a minimalist style with simple shapes, "
                "clean lines, and minimal details"
            ),
            "pixel_art": (
                "in a retro pixel art style, 8-bit aesthetic with nostalgic charm"
            ),
            "realistic": (
                "in a realistic, detailed style with lifelike "
                "appearance and photorealistic quality"
            ),
        }

    def build_prompt(self, spec: EmojiSpecification) -> str:
        """Build an optimized prompt from the specification.

        Args:
            spec: The emoji specification containing description, context, and style

        Returns:
            An optimized prompt string ready for gpt-image-1
        """
        if not spec or not spec.description:
            raise ValueError("Specification must have a description")

        # Extract themes from context
        themes = self.extract_themes(spec.context)

        # Merge description with context intelligently
        merged_content = self.merge_description_and_context(
            spec.description, spec.context, themes
        )

        # Apply style modifiers if specified
        if spec.style:
            style_value = spec.style.style_type.value
            merged_content = self.apply_style_modifiers(merged_content, style_value)

        # Add standard emoji requirements
        with_requirements = self.add_emoji_requirements(merged_content)

        # Optimize length
        optimized = self.optimize_prompt_length(with_requirements)

        return optimized

    def extract_themes(self, context: str) -> list[str]:
        """Extract meaningful themes and emotions from context.

        Args:
            context: The context string to analyze

        Returns:
            List of identified themes
        """
        if not context:
            return []

        themes = []
        context_lower = context.lower()

        # Achievement and success themes
        if any(
            word in context_lower
            for word in ["shipped", "launched", "completed", "finished", "delivered"]
        ):
            themes.append("achievement")
        if any(
            word in context_lower for word in ["success", "successful", "win", "won"]
        ):
            themes.append("success")

        # Team and collaboration themes
        if any(
            word in context_lower
            for word in ["team", "together", "collaboration", "group"]
        ):
            themes.append("teamwork")

        # Time and effort themes
        if any(
            word in context_lower
            for word in ["late", "night", "weekend", "overtime", "dedication"]
        ):
            themes.append("dedication")

        # Emotion themes
        if any(
            word in context_lower
            for word in ["happy", "joy", "excited", "celebration", "celebrate"]
        ):
            themes.append("joy")
        if any(word in context_lower for word in ["proud", "pride", "accomplishment"]):
            themes.append("pride")

        # Challenge themes
        if any(
            word in context_lower
            for word in ["difficult", "challenge", "hard", "complex", "tough"]
        ):
            themes.append("challenge")

        # Innovation themes
        if any(
            word in context_lower for word in ["new", "innovative", "creative", "first"]
        ):
            themes.append("innovation")

        return list(set(themes))  # Remove duplicates

    def merge_description_and_context(
        self, description: str, context: str, themes: list[str]
    ) -> str:
        """Intelligently merge description with context and themes.

        Args:
            description: The main description of the emoji
            context: The context in which the emoji is requested
            themes: Extracted themes from the context

        Returns:
            A merged string that combines all elements intelligently
        """
        # Start with the description as the core concept
        parts = [description]

        # Add only the most relevant theme
        if "achievement" in themes or "success" in themes:
            parts.append("with success")
        elif "teamwork" in themes:
            parts.append("team effort")
        elif "joy" in themes or "pride" in themes:
            parts.append("joyful")

        # Extract one key contextual element
        context_words = context.lower().split()
        for word in context_words:
            if any(key in word for key in ["feature", "launch", "deploy", "release"]):
                parts.append(f"for {word}")
                break

        return " ".join(parts)

    def apply_style_modifiers(self, base_prompt: str, style: str) -> str:
        """Apply style-specific modifiers to the prompt.

        Args:
            base_prompt: The base prompt to modify
            style: The style to apply

        Returns:
            The prompt with style modifiers applied
        """
        if style in self.style_modifiers:
            return f"{base_prompt} {self.style_modifiers[style]}"
        return base_prompt

    def add_emoji_requirements(self, prompt: str) -> str:
        """Add standard requirements for emoji generation.

        Args:
            prompt: The prompt to enhance

        Returns:
            The prompt with emoji requirements added
        """
        requirements = "as a simple emoji icon"
        return f"{prompt} {requirements}"

    def optimize_prompt_length(self, prompt: str) -> str:
        """Optimize prompt length while preserving key information.

        Args:
            prompt: The prompt to optimize

        Returns:
            An optimized prompt within the length limit
        """
        if len(prompt) <= self.max_prompt_length:
            return prompt

        # Truncate and add ellipsis
        truncated = prompt[: self.max_prompt_length - 3] + "..."

        # Try to truncate at a word boundary
        last_space = truncated.rfind(" ", 0, self.max_prompt_length - 10)
        if last_space > 0:
            truncated = prompt[:last_space] + "..."

        return truncated

    def extract_keywords(self, message: str) -> list[str]:
        """Extract relevant keywords from the original message.

        Args:
            message: The original message to extract keywords from

        Returns:
            List of relevant keywords
        """
        # Define common stopwords to filter out
        stopwords = {
            "the",
            "is",
            "at",
            "which",
            "on",
            "a",
            "an",
            "as",
            "are",
            "was",
            "were",
            "been",
            "be",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "shall",
            "to",
            "of",
            "in",
            "for",
            "with",
            "about",
            "against",
            "between",
            "into",
            "through",
            "during",
            "before",
            "after",
            "above",
            "below",
            "up",
            "down",
            "out",
            "off",
            "over",
            "under",
            "again",
            "further",
            "then",
            "once",
            "very",
            "just",
            "also",
            "too",
        }

        # Split message into words and convert to lowercase
        words = message.lower().split()

        # Extract keywords by filtering out stopwords and short words
        keywords = []
        for word in words:
            # Remove common punctuation
            cleaned_word = word.strip(",.!?;:()[]{}\"'")
            if (
                cleaned_word
                and len(cleaned_word) > 2
                and cleaned_word not in stopwords
                and cleaned_word not in keywords  # Avoid duplicates
            ):
                keywords.append(cleaned_word)

        return keywords
