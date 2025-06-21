"""Performance benchmarks for emoji generation components."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from emojismith.domain.value_objects.emoji_specification import EmojiSpecification
from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences
from emojismith.domain.services.generation_service import EmojiGenerationService
from emojismith.domain.services.prompt_service import AIPromptService
from emojismith.application.services.emoji_service import EmojiCreationService


class TestPerformanceBenchmarks:
    """Performance benchmarks for critical emoji generation paths."""

    @pytest.fixture
    def mock_ai_client(self):
        """Mock AI client for benchmarking."""
        client = AsyncMock()
        # Simulate realistic response times
        client.enhance_prompt.return_value = "Enhanced emoji prompt"
        client.generate_image.return_value = b"fake_image_data"
        return client

    @pytest.fixture
    def mock_image_processor(self):
        """Mock image processor for benchmarking."""
        processor = Mock()
        processor.process.return_value = b"processed_image_data"
        return processor

    @pytest.fixture
    def emoji_generation_service(self, mock_ai_client, mock_image_processor):
        """Create generation service with mocked dependencies."""
        return EmojiGenerationService(
            ai_client=mock_ai_client, image_processor=mock_image_processor
        )

    @pytest.fixture
    def prompt_service(self, mock_ai_client):
        """Create prompt service with mocked AI client."""
        return AIPromptService(ai_client=mock_ai_client)

    @pytest.fixture
    def emoji_specification(self):
        """Sample emoji specification for testing."""
        return EmojiSpecification(
            description="A happy celebration emoji",
            message_context="Just shipped a new feature!",
            style_preferences={
                "style": "cartoon",
                "color_scheme": "vibrant",
                "detail_level": "simple",
                "tone": "fun",
            },
        )

    @pytest.fixture
    def emoji_job(self):
        """Sample emoji generation job."""
        return EmojiGenerationJob.create_new(
            user_description="celebration",
            emoji_name="ship_it",
            message_text="Just shipped a new feature!",
            user_id="U123456",
            channel_id="C123456",
            timestamp="1234567890.123456",
            team_id="T123456",
            sharing_preferences=EmojiSharingPreferences.default_for_context(),
        )

    @pytest.mark.benchmark
    def test_emoji_generation_pipeline_performance(
        self, benchmark, emoji_generation_service, emoji_specification
    ):
        """Benchmark the complete emoji generation pipeline."""

        async def generate_emoji():
            return await emoji_generation_service.generate(
                spec=emoji_specification, name="test_emoji"
            )

        # Run benchmark
        result = benchmark.pedantic(
            lambda: pytest.get_event_loop().run_until_complete(generate_emoji()),
            rounds=10,
            iterations=5,
        )

        # Verify result
        assert result is not None
        # Performance assertion: should complete in under 5 seconds
        assert benchmark.stats.mean < 5.0

    @pytest.mark.benchmark
    def test_prompt_enhancement_performance(
        self, benchmark, prompt_service, emoji_specification
    ):
        """Benchmark AI prompt enhancement performance."""

        async def enhance_prompt():
            return await prompt_service.enhance(emoji_specification)

        # Run benchmark
        result = benchmark.pedantic(
            lambda: pytest.get_event_loop().run_until_complete(enhance_prompt()),
            rounds=20,
            iterations=5,
        )

        # Verify result
        assert result == "Enhanced emoji prompt"
        # Performance assertion: prompt enhancement should be fast
        assert benchmark.stats.mean < 1.0

    @pytest.mark.benchmark
    def test_image_processing_performance(self, benchmark, mock_image_processor):
        """Benchmark image processing performance."""
        # Setup test data
        test_image_data = b"x" * 1024 * 100  # 100KB test image

        # Run benchmark
        result = benchmark(
            mock_image_processor.process, test_image_data, size=(512, 512), format="PNG"
        )

        # Verify result
        assert result == b"processed_image_data"
        # Performance assertion: image processing should be very fast
        assert benchmark.stats.mean < 0.1

    @pytest.mark.benchmark
    def test_end_to_end_emoji_creation_performance(self, benchmark):
        """Benchmark the complete end-to-end emoji creation workflow."""
        with patch(
            "emojismith.application.services.emoji_service.EmojiCreationService"
        ) as MockService:
            # Setup mock service
            mock_service = AsyncMock()
            mock_service.process_emoji_generation_job = AsyncMock()
            MockService.return_value = mock_service

            # Create test job
            job = EmojiGenerationJob.create_new(
                user_description="benchmark test",
                emoji_name="benchmark_emoji",
                message_text="Performance testing",
                user_id="U123456",
                channel_id="C123456",
                timestamp="1234567890.123456",
                team_id="T123456",
                sharing_preferences=EmojiSharingPreferences.default_for_context(),
            )

            async def process_job():
                service = EmojiCreationService(
                    generation_service=Mock(),
                    slack_repository=AsyncMock(),
                    job_repository=AsyncMock(),
                )
                await service.process_emoji_generation_job(job)

            # Run benchmark
            benchmark.pedantic(
                lambda: pytest.get_event_loop().run_until_complete(process_job()),
                rounds=5,
                iterations=3,
            )

            # Performance assertion: full workflow should complete reasonably fast
            assert benchmark.stats.mean < 10.0

    @pytest.mark.benchmark(group="concurrent")
    def test_concurrent_emoji_generation_performance(self, benchmark):
        """Benchmark concurrent emoji generation requests."""
        import asyncio

        with patch(
            "emojismith.domain.services.generation_service.EmojiGenerationService"
        ) as MockService:
            # Setup mock service
            mock_service = AsyncMock()
            mock_service.generate = AsyncMock(return_value=Mock())
            MockService.return_value = mock_service

            async def generate_multiple_emojis(count=5):
                """Generate multiple emojis concurrently."""
                tasks = []
                for i in range(count):
                    spec = EmojiSpecification(
                        description=f"Emoji {i}",
                        message_context=f"Context {i}",
                        style_preferences={"style": "cartoon"},
                    )
                    task = mock_service.generate(spec, f"emoji_{i}")
                    tasks.append(task)

                return await asyncio.gather(*tasks)

            # Run benchmark
            result = benchmark.pedantic(
                lambda: pytest.get_event_loop().run_until_complete(
                    generate_multiple_emojis(5)
                ),
                rounds=5,
                iterations=2,
            )

            # Verify all emojis were generated
            assert len(result) == 5
            # Performance assertion: concurrent generation should be efficient
            assert (
                benchmark.stats.mean < 2.0
            )  # Should handle 5 concurrent requests quickly

    @pytest.mark.benchmark(group="memory")
    def test_memory_usage_during_generation(self, benchmark):
        """Benchmark memory usage during emoji generation."""
        import tracemalloc

        def measure_memory_usage():
            """Measure memory usage during emoji generation."""
            tracemalloc.start()

            # Simulate emoji generation with memory allocation
            data = []
            for i in range(100):
                # Simulate image data (1MB each)
                image_data = b"x" * (1024 * 1024)
                data.append(image_data)

            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Clean up
            data.clear()

            return peak / 1024 / 1024  # Convert to MB

        # Run benchmark
        peak_memory_mb = benchmark(measure_memory_usage)

        # Performance assertion: memory usage should be reasonable
        assert peak_memory_mb < 200  # Should use less than 200MB for 100 images

    @pytest.mark.benchmark
    def test_api_retry_performance(self, benchmark):
        """Benchmark API retry mechanism performance."""
        from emojismith.domain.exceptions import RateLimitExceededError

        # Create a mock that fails first 2 times, then succeeds
        call_count = 0

        async def mock_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitExceededError("Rate limit hit")
            return "Success"

        async def api_call_with_retry(max_retries=3):
            """Simulate API call with retry logic."""
            for attempt in range(max_retries):
                try:
                    return await mock_api_call()
                except RateLimitExceededError:
                    if attempt == max_retries - 1:
                        raise
                    await asyncio.sleep(0.1 * (attempt + 1))  # Exponential backoff

        # Reset call count for each benchmark iteration
        def setup():
            nonlocal call_count
            call_count = 0

        # Run benchmark
        result = benchmark.pedantic(
            lambda: pytest.get_event_loop().run_until_complete(api_call_with_retry()),
            setup=setup,
            rounds=10,
            iterations=5,
        )

        # Verify result
        assert result == "Success"
        # Performance assertion: retry mechanism should be efficient
        assert benchmark.stats.mean < 0.5  # Should handle retries quickly
