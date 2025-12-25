"""Tests for webhook Lambda instrumentation."""

import logging
from types import SimpleNamespace

from fastapi.testclient import TestClient

from emojismith.infrastructure.aws import webhook_handler
from shared.infrastructure.logging import trace_id_var


def test_slack_events_sets_trace_and_logs(monkeypatch, caplog):
    """The slack_events route should assign a trace_id and log the receipt."""

    captured: list[str] = []

    async def handle_event(body, headers):
        captured.append(trace_id_var.get())
        return {"ok": True}

    dummy_handler = SimpleNamespace(handle_event=handle_event)

    monkeypatch.setattr(
        webhook_handler, "create_webhook_handler", lambda: (dummy_handler, None)
    )
    webhook_handler._app = None
    webhook_handler._handler = None
    trace_id_var.set("no-trace-id")

    app = webhook_handler._create_app()
    client = TestClient(app)

    with caplog.at_level(logging.INFO):
        response = client.post("/slack/events", content=b"{}")

    assert response.status_code == 200
    assert captured
    assert captured[0] != "no-trace-id"

    webhook_logs = [
        record
        for record in caplog.records
        if getattr(record, "event_data", {}).get("event") == "webhook_received"
    ]
    assert webhook_logs
    assert webhook_logs[0].event_data["endpoint"] == "/slack/events"
