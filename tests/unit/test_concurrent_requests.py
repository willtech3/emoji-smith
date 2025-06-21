"""Tests for concurrent request handling in emoji generation."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import time

from shared.domain.entities import EmojiGenerationJob
from shared.domain.value_objects import EmojiSharingPreferences
from emojismith.application.services.emoji_service import EmojiCreationService
from emojismith.infrastructure.aws.worker_handler import handler as worker_handler
from webhook.handler import WebhookHandler


class TestConcurrentRequests:
    """Test concurrent request handling capabilities."""

    @pytest.fixture
    def mock_generation_service(self):
        """Mock generation service that simulates processing time."""
        service = AsyncMock()

        async def generate_with_delay(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return Mock(image_data=b"fake_image", name=kwargs.get("name", "test"))

        service.generate = generate_with_delay
        return service

    @pytest.fixture
    def emoji_service(self, mock_generation_service):
        """Create emoji service with mocked dependencies."""
        return EmojiCreationService(
            slack_repo=AsyncMock(),
            emoji_generator=mock_generation_service,
            job_queue=AsyncMock(),
        )

    @pytest.fixture
    def webhook_handler(self):
        """Create webhook handler for concurrent testing."""
        mock_slack_repo = AsyncMock()
        mock_job_queue = AsyncMock()
        handler = WebhookHandler(slack_repo=mock_slack_repo, job_queue=mock_job_queue)
        return handler, mock_slack_repo, mock_job_queue

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

    async def test_concurrent_webhook_requests(self, webhook_handler):
        """Test that webhook handler can handle multiple concurrent requests."""
        handler, mock_slack_repo, _ = webhook_handler

        # Create multiple message action payloads
        payloads = []
        for i in range(10):
            payload = {
                "type": "message_action",
                "callback_id": "create_emoji_reaction",
                "trigger_id": f"trigger_{i}",
                "user": {"id": f"U{i}", "name": f"user{i}"},
                "channel": {"id": "C123", "name": "general"},
                "message": {
                    "text": f"Message {i}",
                    "ts": f"123456789{i}.123456",
                    "user": f"U{i}",
                },
                "team": {"id": "T123"},
            }
            payloads.append(payload)

        # Process requests concurrently
        start_time = time.time()
        tasks = [handler.handle_message_action(payload) for payload in payloads]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()

        # Assert all succeeded
        for result in results:
            assert result == {"status": "ok"}

        # Verify all modals were opened through the mock
        assert mock_slack_repo.open_modal.call_count == 10

        # Should handle all requests quickly
        assert end_time - start_time < 1.0

    async def test_concurrent_modal_submissions(self, webhook_handler):
        """Test concurrent modal submission handling."""
        handler, _, mock_job_queue = webhook_handler

        # Create multiple modal submission payloads
        submissions = []
        for i in range(5):
            modal_payload = {
                "type": "view_submission",
                "view": {
                    "callback_id": "emoji_creation_modal",
                    "state": {"values": self._create_modal_values(f"emoji_{i}")},
                    "private_metadata": (
                        f'{{"message_text": "test {i}", "user_id": "U{i}", '
                        f'"channel_id": "C123", "timestamp": "{i}.456", '
                        '"team_id": "T123"}'
                    ),
                },
            }
            submissions.append(modal_payload)

        # Process submissions concurrently
        tasks = [handler.handle_modal_submission(payload) for payload in submissions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert all succeeded
        for result in results:
            assert result == {"response_action": "clear"}

        # Verify all jobs were queued through the mock
        assert mock_job_queue.enqueue_job.call_count == 5

    @pytest.mark.timeout(5)
    async def test_worker_handles_concurrent_sqs_messages(self):
        """Test worker Lambda handling multiple SQS messages concurrently."""
        # Create batch event with multiple messages
        batch_event = {
            "Records": [
                {
                    "messageId": f"msg-{i}",
                    "receiptHandle": f"receipt-{i}",
                    "body": self._create_sqs_message_body(i),
                }
                for i in range(3)
            ]
        }

        # Mock Lambda context
        context = Mock()
        context.remaining_time_in_millis = lambda: 30000

        with patch(
            "emojismith.infrastructure.aws.worker_handler.create_worker_emoji_service"
        ) as mock_create:
            # Create mock service that simulates concurrent processing
            async def process_with_delay(job):
                await asyncio.sleep(0.2)  # Simulate processing
                return None

            mock_service = Mock()
            mock_service.process_emoji_generation_job = process_with_delay
            mock_create.return_value = mock_service

            with patch("asyncio.run") as mock_run:
                # Make asyncio.run actually run the coroutine
                mock_run.side_effect = (
                    lambda coro: asyncio.get_event_loop().run_until_complete(coro)
                )

                # Process messages
                start_time = time.time()
                result = worker_handler(batch_event, context)
                end_time = time.time()

                # Should process successfully
                assert result == {"batchItemFailures": []}

                # Should process concurrently (3 * 0.2s = 0.6s if sequential)
                assert end_time - start_time < 0.5

    async def test_rate_limiting_under_concurrent_load(self, emoji_service):
        """Test rate limiting behavior under concurrent load."""
        from emojismith.domain.exceptions import RateLimitExceededError

        # Configure mock to simulate rate limiting after 3 requests
        request_count = 0

        async def generate_with_rate_limit(*args, **kwargs):
            nonlocal request_count
            request_count += 1
            if request_count > 3:
                raise RateLimitExceededError("Rate limit exceeded")
            await asyncio.sleep(0.05)
            return Mock(image_data=b"fake_image")

        emoji_service.generation_service.generate = generate_with_rate_limit

        # Create 10 concurrent jobs
        jobs = [
            EmojiGenerationJob.create_new(
                user_description=f"emoji_{i}",
                emoji_name=f"test_{i}",
                message_text="test",
                user_id=f"U{i}",
                channel_id="C123",
                timestamp=f"{i}.456",
                team_id="T123",
                sharing_preferences=EmojiSharingPreferences.default_for_context(),
            )
            for i in range(10)
        ]

        # Process concurrently
        tasks = [emoji_service.process_emoji_generation_job(job) for job in jobs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # First 3 should succeed, rest should fail with rate limit
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        rate_limit_count = sum(
            1 for r in results if isinstance(r, RateLimitExceededError)
        )

        assert success_count == 3
        assert rate_limit_count == 7

    async def test_concurrent_requests_with_different_priorities(self, webhook_handler):
        """Test handling concurrent requests with different priority levels."""
        # Create mix of regular and priority requests
        regular_payloads = []
        priority_payloads = []

        for i in range(5):
            # Regular request
            regular_payloads.append(
                {
                    "type": "message_action",
                    "callback_id": "create_emoji_reaction",
                    "trigger_id": f"regular_{i}",
                    "user": {"id": f"U{i}", "name": f"user{i}"},
                    "channel": {"id": "C123", "name": "general"},
                    "message": {
                        "text": f"Regular {i}",
                        "ts": f"{i}.456",
                        "user": f"U{i}",
                    },
                    "team": {"id": "T123"},
                }
            )

            # Priority request (e.g., from paid tier)
            priority_payloads.append(
                {
                    "type": "message_action",
                    "callback_id": "create_emoji_reaction",
                    "trigger_id": f"priority_{i}",
                    "user": {"id": f"UP{i}", "name": f"priority_user{i}"},
                    "channel": {"id": "C456", "name": "priority"},
                    "message": {
                        "text": f"Priority {i}",
                        "ts": f"{i}.789",
                        "user": f"UP{i}",
                    },
                    "team": {"id": "T456"},  # Different team ID could indicate priority
                }
            )

        # Process all requests concurrently
        all_payloads = regular_payloads + priority_payloads
        tasks = [webhook_handler.handle_message_action(p) for p in all_payloads]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert all(r == {"status": "ok"} for r in results)
        assert webhook_handler.slack_repo.open_modal.call_count == 10

    async def test_graceful_degradation_under_high_concurrency(self, emoji_service):
        """Test system behavior under extremely high concurrent load."""
        # Create 50 concurrent jobs
        jobs = [
            EmojiGenerationJob.create_new(
                user_description=f"high_load_{i}",
                emoji_name=f"load_test_{i}",
                message_text="Load test",
                user_id=f"U{i}",
                channel_id="C123",
                timestamp=f"{i}.456",
                team_id="T123",
                sharing_preferences=EmojiSharingPreferences.default_for_context(),
            )
            for i in range(50)
        ]

        # Set up generation service to simulate resource constraints
        processing_count = 0
        max_concurrent = 10

        async def generate_with_limit(*args, **kwargs):
            nonlocal processing_count
            if processing_count >= max_concurrent:
                # Simulate resource exhaustion
                raise Exception("Too many concurrent requests")

            processing_count += 1
            try:
                await asyncio.sleep(0.1)
                return Mock(image_data=b"fake_image")
            finally:
                processing_count -= 1

        emoji_service.generation_service.generate = generate_with_limit

        # Process all jobs
        tasks = [emoji_service.process_emoji_generation_job(job) for job in jobs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Some should succeed, some should fail due to limits
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))

        assert successes > 0  # At least some should succeed
        assert failures > 0  # Some should fail due to limits
        assert successes + failures == 50

    # Helper methods
    def _create_modal_values(self, emoji_name):
        """Create modal form values for testing."""
        return {
            "emoji_name": {"name": {"value": emoji_name}},
            "emoji_description": {
                "description": {"value": f"Description for {emoji_name}"}
            },
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

    def _create_sqs_message_body(self, index):
        """Create SQS message body for testing."""
        import json

        return json.dumps(
            {
                "job_id": f"job-{index}",
                "message_text": f"Message {index}",
                "user_description": f"Emoji {index}",
                "emoji_name": f"emoji_{index}",
                "user_id": f"U{index}",
                "channel_id": "C123456",
                "timestamp": f"123456789{index}.123456",
                "team_id": "T123456",
                "status": "PENDING",
                "created_at": datetime.utcnow().isoformat(),
                "sharing_preferences": {
                    "share_location": "channel",
                    "instruction_visibility": "EVERYONE",
                    "image_size": "EMOJI_SIZE",
                },
            }
        )
