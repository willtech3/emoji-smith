import json
import time
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from emojismith.presentation.web.slack_webhook_api import create_webhook_api
from emojismith.application.handlers.slack_webhook_handler import (
    SlackWebhookHandler,
    WebhookEventProcessor,
    UnauthorizedError,
)
from webhook.handler import WebhookHandler
from webhook.infrastructure.slack_signature_validator import SlackSignatureValidator
from webhook.security.webhook_security_service import WebhookSecurityService
from shared.domain.repositories import SlackModalRepository, JobQueueProducer
from shared.domain.entities import EmojiGenerationJob


@pytest.fixture()
def app_env():
    signing_secret = b"test_secret"
    slack_repo = AsyncMock(spec=SlackModalRepository)
    slack_repo.open_modal.return_value = None
    job_queue = AsyncMock(spec=JobQueueProducer)
    webhook_handler = WebhookHandler(slack_repo=slack_repo, job_queue=job_queue)
    validator = SlackSignatureValidator(signing_secret=signing_secret)
    security = WebhookSecurityService(signature_validator=validator)
    processor = WebhookEventProcessor(webhook_handler)
    handler = SlackWebhookHandler(security, processor)
    app = create_webhook_api(handler)
    client = TestClient(app)
    return client, slack_repo, job_queue, validator


def _headers(validator: SlackSignatureValidator, body: bytes) -> dict:
    timestamp = str(int(time.time()))
    sig_base = f"v0:{timestamp}:".encode() + body
    signature = validator._compute_expected_signature(sig_base)
    return {
        "X-Slack-Request-Timestamp": timestamp,
        "X-Slack-Signature": signature,
        "Content-Type": "application/json",
    }


def test_webhook_http_flow_success(app_env):
    client, slack_repo, job_queue, validator = app_env
    message_payload = {
        "type": "message_action",
        "callback_id": "create_emoji_reaction",
        "trigger_id": "123.456",
        "user": {"id": "U12345"},
        "channel": {"id": "C67890"},
        "message": {"text": "deploy", "ts": "111.222", "user": "U123"},
        "team": {"id": "T11111"},
    }
    body = json.dumps(message_payload).encode()
    resp = client.post("/slack/events", content=body, headers=_headers(validator, body))
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    slack_repo.open_modal.assert_awaited_once()

    modal_payload = {
        "type": "view_submission",
        "view": {
            "callback_id": "emoji_creation_modal",
            "state": {
                "values": {
                    "emoji_name": {"name": {"value": "facepalm"}},
                    "emoji_description": {"description": {"value": "facepalm"}},
                    "share_location": {
                        "share_location_select": {
                            "selected_option": {"value": "channel"}
                        }
                    },
                    "instruction_visibility": {
                        "visibility_select": {"selected_option": {"value": "visible"}}
                    },
                    "image_size": {
                        "size_select": {"selected_option": {"value": "512x512"}}
                    },
                    "style_type": {
                        "style_select": {"selected_option": {"value": "cartoon"}}
                    },
                    "color_scheme": {
                        "color_select": {"selected_option": {"value": "auto"}}
                    },
                    "detail_level": {
                        "detail_select": {"selected_option": {"value": "simple"}}
                    },
                    "tone": {"tone_select": {"selected_option": {"value": "fun"}}},
                }
            },
            "private_metadata": json.dumps(
                {
                    "message_text": "deploy",
                    "user_id": "U12345",
                    "channel_id": "C67890",
                    "timestamp": "111.222",
                    "team_id": "T11111",
                }
            ),
        },
    }
    modal_body = json.dumps(modal_payload).encode()
    resp = client.post(
        "/slack/events", content=modal_body, headers=_headers(validator, modal_body)
    )
    assert resp.status_code == 200
    assert resp.json() == {"response_action": "clear"}
    job_queue.enqueue_job.assert_awaited_once()
    job = job_queue.enqueue_job.call_args.args[0]
    assert isinstance(job, EmojiGenerationJob)
    assert job.user_id == "U12345"
    assert job.channel_id == "C67890"


def test_webhook_invalid_signature(app_env):
    client, _, _, validator = app_env
    payload = {"type": "message_action", "callback_id": "create_emoji_reaction"}
    body = json.dumps(payload).encode()
    headers = _headers(validator, body)
    headers["X-Slack-Signature"] = "v0=invalid"
    with pytest.raises(UnauthorizedError):
        client.post("/slack/events", content=body, headers=headers)
