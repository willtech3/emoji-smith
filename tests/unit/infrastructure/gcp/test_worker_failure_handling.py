"""Worker behaviour when a job cannot be completed."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from emojismith.domain.errors import ImageGenerationRejectedError

JOB = {
    "job_id": "job_123",
    "trace_id": "trace_123",
    "user_description": "facepalm reaction",
    "message_text": "Just deployed on Friday!",
    "user_id": "U12345",
    "channel_id": "C67890",
    "timestamp": "1234567890.123456",
    "team_id": "T11111",
    "emoji_name": "facepalm_reaction",
    "status": "PENDING",
    "sharing_preferences": {},
    "created_at": "2026-01-31T00:00:00+00:00",
    "image_provider": "openai",
}


def _envelope(delivery_attempt: int | None = None) -> dict:
    data = base64.b64encode(json.dumps(JOB).encode()).decode()
    envelope: dict = {"message": {"messageId": "msg-1", "data": data}}
    if delivery_attempt is not None:
        envelope["deliveryAttempt"] = delivery_attempt
    return envelope


@pytest.fixture()
def failing_service(monkeypatch):
    from emojismith.infrastructure.gcp import worker_app

    service = MagicMock()
    service.process_emoji_generation_job = AsyncMock(side_effect=RuntimeError("boom"))
    service.notify_generation_failed = AsyncMock()
    monkeypatch.setattr(
        worker_app, "create_worker_emoji_service", lambda **_kwargs: service
    )
    return service, TestClient(worker_app.app)


@pytest.mark.unit()
class TestWorkerFailureHandling:
    def test_pubsub_push_on_early_failure_retries_without_notifying(
        self, failing_service
    ):
        service, client = failing_service

        resp = client.post("/pubsub", json=_envelope(delivery_attempt=1))

        assert resp.status_code == 500
        service.notify_generation_failed.assert_not_awaited()

    def test_pubsub_push_on_final_attempt_notifies_requester(self, failing_service):
        """The last delivery before dead-lettering is the last chance to tell them."""
        service, client = failing_service

        resp = client.post("/pubsub", json=_envelope(delivery_attempt=5))

        assert resp.status_code == 500
        service.notify_generation_failed.assert_awaited_once()
        job, error = service.notify_generation_failed.call_args.args
        assert job.user_id == "U12345"
        assert isinstance(error, RuntimeError)

    def test_pubsub_push_on_policy_refusal_notifies_and_acknowledges(
        self, failing_service
    ):
        """Retrying a refused prompt cannot succeed, so it must not be retried."""
        service, client = failing_service
        service.process_emoji_generation_job.side_effect = ImageGenerationRejectedError(
            "blocked"
        )

        resp = client.post("/pubsub", json=_envelope(delivery_attempt=1))

        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"
        service.notify_generation_failed.assert_awaited_once()

    def test_pubsub_push_when_notification_fails_still_requests_retry(
        self, failing_service
    ):
        service, client = failing_service
        service.notify_generation_failed.side_effect = RuntimeError("slack down")

        resp = client.post("/pubsub", json=_envelope(delivery_attempt=5))

        assert resp.status_code == 500

    def test_max_delivery_attempts_matches_terraform_dead_letter_policy(self):
        from emojismith.infrastructure.gcp import worker_app

        repo_root = Path(__file__).resolve().parents[4]
        terraform = (repo_root / "terraform" / "pubsub.tf").read_text()
        match = re.search(r"max_delivery_attempts\s*=\s*(\d+)", terraform)

        assert match is not None
        assert int(match.group(1)) == worker_app.MAX_DELIVERY_ATTEMPTS
