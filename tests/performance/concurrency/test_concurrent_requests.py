"""Tests for concurrent request handling in emoji generation."""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from emojismith.application.services.emoji_service import EmojiCreationService
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences


@pytest.mark.performance()
class TestConcurrentRequests:
    """Test concurrent request handling capabilities."""

    @pytest.fixture()
    def mock_image_generator(self):
        """Mock image generator that simulates processing time."""
        generator = AsyncMock()

        async def generate_with_delay(prompt):
            await asyncio.sleep(0.1)  # Simulate processing time
            return b"fake_image"

        generator.generate_image = generate_with_delay
        return generator

    @pytest.fixture()
    def mock_image_generator_factory(self, mock_image_generator):
        """Mock factory that creates image generators."""
        factory = MagicMock()
        factory.create.return_value = mock_image_generator
        return factory

    @pytest.fixture()
    def mock_build_prompt_use_case(self):
        """Mock build prompt use case that returns a simple prompt."""
        mock = AsyncMock()
        mock.build_prompt.return_value = "test prompt"
        return mock

    @pytest.fixture()
    def emoji_service(self, mock_image_generator_factory, mock_build_prompt_use_case):
        """Create emoji service with mocked dependencies."""
        mock_image_processor = MagicMock()
        mock_image_processor.process_for_slack.return_value = b"processed_image"

        mock_emoji_validator = MagicMock()
        mock_emoji_validator.validate_name.return_value = True

        return EmojiCreationService(
            slack_repo=AsyncMock(),
            build_prompt_use_case=mock_build_prompt_use_case,
            image_generator_factory=mock_image_generator_factory,
            image_processor=mock_image_processor,
            emoji_validator=mock_emoji_validator,
            style_template_manager=MagicMock(),
            file_sharing_repo=AsyncMock(),
        )

    async def test_multiple_concurrent_emoji_generations(self, emoji_service):
        """Test that multiple emoji generations can run concurrently."""
        # Create multiple jobs
        jobs = []
        for i in range(5):
            job = EmojiGenerationJob.create_new(
                user_description=f"emoji_{i}",
                emoji_name=f"test_emoji_{i}",
                message_text=f"Test message {i}",
                user_id=f"U{i}",
                channel_id="C123456",
                timestamp=f"123456789{i}.123456",
                team_id="T123456",
                sharing_preferences=EmojiSharingPreferences.default_for_context(),
            )
            jobs.append(job)

        # Process jobs concurrently
        start_time = time.time()
        tasks = [emoji_service.process_emoji_generation_job(job) for job in jobs]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Assert all completed successfully
        for result in results:
            assert not isinstance(result, Exception)

        # Verify concurrent execution (should be faster than sequential)
        elapsed_time = end_time - start_time
        assert elapsed_time < 0.6  # 5 jobs * 0.1s each = 0.5s if sequential
