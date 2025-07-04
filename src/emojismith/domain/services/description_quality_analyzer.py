"""Service for analyzing emoji description quality and generating fallbacks."""


class DescriptionQualityAnalyzer:
    """Analyze description quality and provide fallback strategies."""

    VAGUE_TERMS: set[str] = {
        "emoji",
        "nice",
        "good",
        "bad",
        "thing",
        "stuff",
        "icon",
        "image",
        "one",
        "some",
        "any",
        "ok",
        "okay",
    }

    MIN_MEANINGFUL_WORDS = 2

    VISUAL_TERMS: set[str] = {
        "color",
        "colorful",
        "bright",
        "dark",
        "light",
        "shape",
        "size",
        "style",
        "look",
        "appearance",
        "red",
        "blue",
        "green",
        "yellow",
        "orange",
        "purple",
        "pink",
        "black",
        "white",
        "gray",
        "grey",
        "small",
        "big",
        "large",
        "tiny",
        "huge",
        "round",
        "square",
        "shiny",
        "matte",
        "glossy",
        "transparent",
        "opaque",
    }

    EMOTION_TERMS: set[str] = {
        "happy",
        "sad",
        "angry",
        "excited",
        "tired",
        "sleepy",
        "energetic",
        "calm",
        "stressed",
        "relaxed",
        "worried",
        "confident",
        "nervous",
        "joyful",
        "frustrated",
        "content",
        "anxious",
        "proud",
        "surprised",
    }

    ACTION_TERMS: set[str] = {
        "running",
        "jumping",
        "dancing",
        "sleeping",
        "working",
        "playing",
        "eating",
        "drinking",
        "flying",
        "swimming",
        "walking",
        "sitting",
        "standing",
        "laughing",
        "crying",
        "smiling",
        "thinking",
        "coding",
    }

    def __init__(self, quality_threshold: float = 0.5) -> None:
        """Initialize the analyzer.

        Args:
            quality_threshold: Threshold below which descriptions are considered
                poor (0-1)
        """
        self.quality_threshold = quality_threshold

    def analyze_description(self, description: str) -> tuple[float, list[str]]:
        """Analyze description quality and return score with improvement suggestions.

        Args:
            description: The emoji description to analyze

        Returns:
            Tuple of (quality_score, list_of_issues)
        """
        if not description:
            return 0.0, ["No description provided"]

        words = description.lower().split()
        issues = []
        score = 1.0

        # Check for single word descriptions
        if len(words) == 1:
            score -= 0.3
            if words[0] in self.VAGUE_TERMS:
                score -= 0.4
                issues.append("Description is too vague")
            else:
                issues.append("Add more descriptive words")

        # Check for vague terms ratio
        vague_count = sum(1 for word in words if word in self.VAGUE_TERMS)
        if len(words) > 0:
            vague_ratio = vague_count / len(words)
            if vague_ratio > 0.5:
                score -= 0.4
                issues.append("Description is too vague")
            elif vague_ratio > 0.25:
                score -= 0.2
                issues.append("Reduce vague terms")

        # Check for meaningful descriptors
        meaningful_words = [
            w for w in words if w not in self.VAGUE_TERMS and len(w) > 2
        ]
        if len(meaningful_words) < self.MIN_MEANINGFUL_WORDS:
            score -= 0.2
            issues.append("Add more descriptive words")

        # Check for visual descriptors
        has_visual = any(word in words for word in self.VISUAL_TERMS)
        if not has_visual and len(words) < 5:
            score -= 0.1
            issues.append("Describe visual appearance")

        # Check for specificity
        has_emotion = any(word in self.EMOTION_TERMS for word in words)
        has_action = any(word in self.ACTION_TERMS for word in words)

        # Bonus for specific descriptors (but cap the total bonus)
        bonus = 0.0
        if has_visual:
            bonus += 0.1
        if has_emotion:
            bonus += 0.05
        if has_action:
            bonus += 0.05

        # Apply bonus but ensure we don't exceed the penalties
        score = score + min(bonus, 1.0 - score)

        # Ensure score stays in valid range
        score = max(0.0, min(1.0, score))

        # Add specific suggestions based on what's missing
        if not has_emotion and not has_action and len(words) < 3:
            issues.append("Describe what the emoji is doing or feeling")

        return score, issues

    def is_poor_quality(self, description: str) -> bool:
        """Check if a description is below the quality threshold.

        Args:
            description: The description to check

        Returns:
            True if the description is poor quality
        """
        score, _ = self.analyze_description(description)
        return score < self.quality_threshold

    def extract_concepts(self, context: str) -> list[str]:
        """Extract key concepts from context.

        Args:
            context: The context string to analyze

        Returns:
            List of key concepts extracted from context
        """
        if not context:
            return []

        # Common words to filter out
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
            "into",
            "through",
            "just",
            "now",
            "then",
            "also",
        }

        words = context.lower().split()
        concepts = []

        # Extract important words
        for word in words:
            cleaned = word.strip(".,!?;:\"'")
            if (
                cleaned
                and len(cleaned) > 2
                and cleaned not in stopwords
                and cleaned not in concepts
            ):
                concepts.append(cleaned)

        # Prioritize action words and nouns
        priority_concepts = []
        for concept in concepts:
            if any(
                keyword in concept
                for keyword in [
                    "deploy",
                    "ship",
                    "launch",
                    "release",
                    "feature",
                    "system",
                    "payment",
                    "authentication",
                    "team",
                    "success",
                    "complete",
                    "finish",
                    "build",
                    "create",
                    "update",
                    "fix",
                    "improve",
                ]
            ):
                priority_concepts.append(concept)

        # Return priority concepts first, then others
        return (
            priority_concepts[:3]
            + [c for c in concepts if c not in priority_concepts][:2]
        )

    def generate_fallback_prompt(self, context: str, poor_description: str) -> str:
        """Generate a better prompt using context when description is poor.

        Args:
            context: The context in which the emoji was requested
            poor_description: The poor quality description provided

        Returns:
            An improved prompt based primarily on context
        """
        # Extract useful words from poor description (non-vague terms)
        desc_words = [
            w
            for w in poor_description.lower().split()
            if w not in self.VAGUE_TERMS and len(w) > 2
        ]

        # Extract concepts from context
        concepts = self.extract_concepts(context)

        # Build fallback prompt
        if concepts:
            # Use context as primary source
            base = f"Emoji representing {concepts[0]}"

            # Add second concept if available
            if len(concepts) > 1:
                base = f"Emoji representing {concepts[0]} and {concepts[1]}"

            # Add any useful words from description
            if desc_words:
                # Check if desc_words contain visual/emotion/action terms
                visual_words = [w for w in desc_words if w in self.VISUAL_TERMS]
                emotion_words = [w for w in desc_words if w in self.EMOTION_TERMS]
                action_words = [w for w in desc_words if w in self.ACTION_TERMS]

                if visual_words:
                    base += f" with {' '.join(visual_words[:2])} appearance"
                elif emotion_words:
                    base += f" feeling {' '.join(emotion_words[:1])}"
                elif action_words:
                    base += f" {' '.join(action_words[:1])}"
                elif desc_words:
                    base += f" with {desc_words[0]} style"

            return base
        else:
            # No context available, try to salvage what we can
            if desc_words:
                return f"{' '.join(desc_words)} emoji icon"
            else:
                return "Simple, friendly emoji icon"
