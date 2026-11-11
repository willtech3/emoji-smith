"""Provider clients must give up before the worker's request timeout."""

import pytest

from emojismith.domain.value_objects.image_provider import ImageProvider
from emojismith.infrastructure.factories.image_generator_factory import (
    ImageGeneratorFactory,
)

WORKER_REQUEST_TIMEOUT_S = 600


@pytest.mark.unit()
class TestImageGeneratorTimeouts:
    def test_openai_client_worst_case_fits_in_worker_timeout(self):
        repo = ImageGeneratorFactory(openai_api_key="sk-test").create(
            ImageProvider.OPENAI
        )

        client = repo._client
        worst_case = client.timeout * (client.max_retries + 1)
        assert worst_case < WORKER_REQUEST_TIMEOUT_S

    def test_gemini_client_worst_case_fits_in_worker_timeout(self):
        repo = ImageGeneratorFactory(google_api_key="test-key").create(
            ImageProvider.GOOGLE_GEMINI
        )

        timeout_ms = repo._client._api_client._http_options.timeout
        assert timeout_ms is not None
        # Primary attempt plus one fallback-model attempt.
        assert (timeout_ms / 1000) * 2 < WORKER_REQUEST_TIMEOUT_S
