"""Tests for OpenAIRepository protocol interface."""

from emojismith.domain.repositories.openai_repository import OpenAIRepository


def test_openai_repository_protocol_methods_exist() -> None:
    """OpenAIRepository protocol defines required methods."""
    assert hasattr(OpenAIRepository, "optimize_prompt")
    assert hasattr(OpenAIRepository, "generate_image")
