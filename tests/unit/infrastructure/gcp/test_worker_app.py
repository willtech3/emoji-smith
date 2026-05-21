from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit()
class TestWorkerApp:
    @pytest.fixture()
    def job_dict(self):
        """Standard Pub/Sub job payload used across all worker tests."""
        return {
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
            "sharing_preferences": {
                "share_location": "channel",
                "instruction_visibility": "EVERYONE",
                "include_upload_instructions": True,
                "image_size": "EMOJI_SIZE",
                "thread_ts": None,
            },
            "created_at": "2026-01-31T00:00:00+00:00",
            "style_preferences": {},
            "generation_preferences": {},
            "image_provider": "openai",
        }

    @pytest.fixture()
    def pubsub_envelope(self, job_dict):
        """Wrap job_dict in a Pub/Sub push envelope."""
        message_data = base64.b64encode(json.dumps(job_dict).encode("utf-8")).decode(
            "utf-8"
        )
        return {
            "message": {"messageId": "msg-1", "data": message_data},
        }

    def test_pubsub_push_processes_job_and_returns_ok(
        self, monkeypatch, pubsub_envelope
    ):
        from emojismith.infrastructure.gcp import worker_app

        mock_service = MagicMock()
        mock_service.process_emoji_generation_job = AsyncMock()
        monkeypatch.setattr(
            worker_app,
            "create_worker_emoji_service",
            lambda **_kwargs: mock_service,
        )

        client = TestClient(worker_app.app)
        resp = client.post("/pubsub", json=pubsub_envelope)

        assert resp.status_code == 200
        assert resp.json() == {"status": "ok", "messageId": "msg-1"}

        mock_service.process_emoji_generation_job.assert_awaited_once()
        processed_job = mock_service.process_emoji_generation_job.call_args.args[0]
        assert processed_job.job_id == "job_123"
        assert processed_job.image_provider == "openai"

    def test_pubsub_push_returns_400_for_invalid_envelope(self):
        from emojismith.infrastructure.gcp import worker_app

        client = TestClient(worker_app.app)
        resp = client.post("/pubsub", json={"not": "a-valid-envelope"})

        assert resp.status_code == 400

    def test_pubsub_push_resets_trace_id_context_var_safely(
        self, monkeypatch, pubsub_envelope
    ):
        from emojismith.infrastructure.gcp import worker_app
        from shared.infrastructure.logging import trace_id_var

        # Ensure the trace var is set to a known value initially
        initial_token = trace_id_var.set("initial_state")

        mock_service = MagicMock()

        async def mock_process(job):
            # Assert that during processing, the trace ID is set
            assert trace_id_var.get() == "trace_123"

        mock_service.process_emoji_generation_job = mock_process
        monkeypatch.setattr(
            worker_app,
            "create_worker_emoji_service",
            lambda **_kwargs: mock_service,
        )

        client = TestClient(worker_app.app)

        try:
            resp = client.post("/pubsub", json=pubsub_envelope)
            assert resp.status_code == 200

            # Verify that AFTER processing is complete, the trace ID is
            # reset back to what it was before (initial_state)
            assert trace_id_var.get() == "initial_state"
        finally:
            trace_id_var.reset(initial_token)

    def test_pubsub_push_resets_trace_id_on_exception(
        self, monkeypatch, pubsub_envelope
    ):
        from emojismith.infrastructure.gcp import worker_app
        from shared.infrastructure.logging import trace_id_var

        initial_token = trace_id_var.set("initial_state")

        mock_service = MagicMock()

        async def mock_process(job):
            # Assert trace_id is correctly set during processing
            assert trace_id_var.get() == "trace_123"
            raise ValueError("Something went wrong")

        mock_service.process_emoji_generation_job = mock_process
        monkeypatch.setattr(
            worker_app,
            "create_worker_emoji_service",
            lambda **_kwargs: mock_service,
        )

        client = TestClient(worker_app.app)

        try:
            resp = client.post("/pubsub", json=pubsub_envelope)
            assert resp.status_code == 500

            # Verify that AFTER an exception, the trace ID is still
            # reset back to the initial state
            assert trace_id_var.get() == "initial_state"
        finally:
            trace_id_var.reset(initial_token)
