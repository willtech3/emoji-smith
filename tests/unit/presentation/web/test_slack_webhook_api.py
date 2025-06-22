from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from emojismith.presentation.web.slack_webhook_api import create_webhook_api


class DummyHandler:
    def __init__(self) -> None:
        self.handle_event = AsyncMock(return_value={"ok": True})

    def health_check(self) -> dict:
        return {"status": "healthy"}


@pytest.mark.unit
def test_routes_delegate_to_handler() -> None:
    handler = DummyHandler()
    app = create_webhook_api(handler)
    client = TestClient(app)

    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}

    resp = client.post("/slack/events", content=b"{}")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    handler.handle_event.assert_awaited_once()
