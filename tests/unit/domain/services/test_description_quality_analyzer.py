"""Tests for DescriptionQualityAnalyzer service."""

from emojismith.domain.services.description_quality_analyzer import (
    DescriptionQualityAnalyzer,
)


class TestDescriptionQualityAnalyzer:
    """Test cases for DescriptionQualityAnalyzer."""

    def test_analyze_vague_single_word_descriptions(self):
        """Test that single vague words get low quality scores."""
        analyzer = DescriptionQualityAnalyzer()

        vague_descriptions = [
            "emoji",
            "nice",
            "good",
            "bad",
            "thing",
            "stuff",
            "icon",
            "image",
        ]

        for desc in vague_descriptions:
            score, issues = analyzer.analyze_description(desc)
            assert score < 0.5, f"'{desc}' should have low score but got {score}"
            assert len(issues) > 0, f"'{desc}' should have issues"
            assert any("vague" in issue.lower() for issue in issues)

    def test_analyze_good_descriptions(self):
        """Test that detailed descriptions get high quality scores."""
        analyzer = DescriptionQualityAnalyzer()

        good_descriptions = [
            "happy dancing robot with blue lights",
            "celebration cake with sparkles and candles",
            "tired developer drinking coffee at night",
            "rocket ship launching into space with flames",
        ]

        for desc in good_descriptions:
            score, issues = analyzer.analyze_description(desc)
            assert score >= 0.7, f"'{desc}' should have high score but got {score}"
            assert len(issues) <= 1, f"'{desc}' should have few issues but got {issues}"

    def test_analyze_medium_quality_descriptions(self):
        """Test descriptions with some detail but room for improvement."""
        analyzer = DescriptionQualityAnalyzer()

        test_cases = [
            ("happy face", 0.8, 1.0),  # Has emotion descriptor, quite good
            ("blue emoji", 0.6, 0.8),  # Has color (visual) but vague term
            ("big celebration", 0.9, 1.0),  # Has size descriptor + meaningful word
            ("simple icon", 0.4, 0.6),  # Basic, not very descriptive
            ("nice thing", 0.2, 0.4),  # Two vague terms, poor quality
        ]

        for desc, min_score, max_score in test_cases:
            score, _issues = analyzer.analyze_description(desc)
            assert min_score <= score <= max_score, (
                f"'{desc}' score {score} not in range [{min_score}, {max_score}]"
            )

    def test_visual_descriptors_improve_score(self):
        """Test that visual descriptors improve the quality score."""
        analyzer = DescriptionQualityAnalyzer()

        # Without visual descriptors
        score1, _ = analyzer.analyze_description("party celebration")

        # With visual descriptors
        score2, _ = analyzer.analyze_description("colorful party celebration")
        score3, _ = analyzer.analyze_description("party celebration with bright colors")

        assert score2 > score1, "Adding 'colorful' should improve score"
        assert score3 > score1, "Adding color description should improve score"

    def test_generate_fallback_prompt_with_good_context(self):
        """Test fallback prompt generation when context is rich."""
        analyzer = DescriptionQualityAnalyzer()

        context = "Team just shipped the new payment feature after weeks of hard work"
        poor_description = "nice"

        fallback = analyzer.generate_fallback_prompt(context, poor_description)

        assert (
            "payment" in fallback.lower()
            or "feature" in fallback.lower()
            or "team" in fallback.lower()
        )
        assert fallback != poor_description
        assert len(fallback) > len(poor_description)

    def test_generate_fallback_prompt_with_no_context(self):
        """Test fallback prompt generation when context is empty."""
        analyzer = DescriptionQualityAnalyzer()

        fallback = analyzer.generate_fallback_prompt("", "emoji")

        assert fallback == "Simple, friendly emoji icon"

    def test_generate_fallback_prompt_preserves_useful_words(self):
        """Test that non-vague words from poor descriptions are preserved."""
        analyzer = DescriptionQualityAnalyzer()

        context = "Celebrating the launch"
        poor_description = "nice rocket emoji"

        fallback = analyzer.generate_fallback_prompt(context, poor_description)

        assert "rocket" in fallback.lower()
        assert "nice" not in fallback.lower()  # Vague term should be filtered

    def test_configurable_quality_threshold(self):
        """Test that quality threshold can be configured."""
        analyzer = DescriptionQualityAnalyzer(quality_threshold=0.8)

        assert analyzer.quality_threshold == 0.8

        # Test is_poor_quality method
        assert analyzer.is_poor_quality("good emoji") is True  # Below 0.8
        assert (
            analyzer.is_poor_quality(
                "detailed robot with glowing blue eyes and metallic finish"
            )
            is False
        )

    def test_extract_concepts_from_context(self):
        """Test concept extraction from context."""
        analyzer = DescriptionQualityAnalyzer()

        context = "Just deployed the new authentication system to production"
        concepts = analyzer.extract_concepts(context)

        assert len(concepts) > 0
        assert any(
            concept in ["deployed", "authentication", "system", "production"]
            for concept in concepts
        )

    def test_suggestions_for_improvement(self):
        """Test that improvement suggestions are specific and helpful."""
        analyzer = DescriptionQualityAnalyzer()

        test_cases = [
            ("emoji", ["too vague", "descriptive words", "visual"]),
            ("red", ["descriptive words", "what"]),
            ("big happy face", []),  # Good enough, minimal suggestions
        ]

        for desc, expected_keywords in test_cases:
            _, issues = analyzer.analyze_description(desc)
            issues_text = " ".join(issues).lower()

            if expected_keywords:
                assert any(keyword in issues_text for keyword in expected_keywords), (
                    f"Expected keywords {expected_keywords} in issues: {issues}"
                )
