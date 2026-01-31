from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.mark.unit()
class TestWorkerApp:
    def test_pubsub_push_processes_job_and_returns_ok(self, monkeypatch):
        from emojismith.infrastructure.gcp import worker_app

        mock_service = MagicMock()
        mock_service.process_emoji_generation_job = AsyncMock()
        monkeypatch.setattr(
            worker_app, "create_worker_emoji_service", lambda: mock_service
        )

        client = TestClient(worker_app.app)

        job_dict = {
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
        message_data = base64.b64encode(json.dumps(job_dict).encode("utf-8")).decode(
            "utf-8"
        )
        envelope = {"message": {"messageId": "msg-1", "data": message_data}}

        resp = client.post("/pubsub", json=envelope)

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
