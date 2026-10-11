"""In-sandbox fake of the three OpenAI endpoints Emoji Smith uses.

The OpenAI SDK honours OPENAI_BASE_URL, so the application's own clients
(OpenAIAPIRepository / ImageGeneratorFactory) talk to this server without code
changes or a real key. Endpoints: GET /v1/models/{id}, POST /v1/responses,
POST /v1/images/generations. Every request is recorded (GET /requests, POST /reset).
Returned images are synthetic PNGs drawn with Pillow; no real model is involved.
"""

from __future__ import annotations

import argparse
import base64
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw

MARKER = "FACTORY-FAKE-ENHANCED"
_LOCK = threading.Lock()
_REQUESTS: list[dict[str, Any]] = []


def _synthetic_png(variant: int) -> bytes:
    img = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    fill = [(255, 196, 0, 255), (90, 200, 120, 255), (90, 150, 255, 255)][variant % 3]
    draw.ellipse((128, 128, 896, 896), fill=fill, outline=(40, 40, 40, 255), width=24)
    draw.ellipse((360, 380, 440, 460), fill=(40, 40, 40, 255))
    draw.ellipse((584, 380, 664, 460), fill=(40, 40, 40, 255))
    draw.arc((320, 420, 704, 760), 20, 160, fill=(40, 40, 40, 255), width=24)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class _Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: Any) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return {}

    def _record(self, entry: dict[str, Any]) -> None:
        entry["auth_header_present"] = bool(self.headers.get("Authorization"))
        with _LOCK:
            _REQUESTS.append(entry)

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send(200, {"status": "ok", "service": "fake-openai"})
        elif path == "/requests":
            with _LOCK:
                self._send(200, {"requests": list(_REQUESTS)})
        elif path.startswith("/v1/models/"):
            model = path[len("/v1/models/") :]
            self._record({"endpoint": "models.retrieve", "model": model})
            self._send(
                200,
                {
                    "id": model,
                    "object": "model",
                    "created": 1700000000,
                    "owned_by": "factory-fake",
                },
            )
        else:
            self._send(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0]
        if path == "/reset":
            with _LOCK:
                _REQUESTS.clear()
            self._send(200, {"status": "reset"})
            return
        body = self._json_body()
        if path == "/v1/responses":
            model = body.get("model", "")
            roles = [m.get("role") for m in body.get("input", []) if isinstance(m, dict)]
            self._record({"endpoint": "responses.create", "model": model, "input_roles": roles})
            text = (
                f"{MARKER} flat cartoon emoji icon, single centered subject, bold "
                "silhouette, high contrast colors, optimized for 128x128 Slack emoji, "
                "transparent background"
            )
            self._send(
                200,
                {
                    "id": "resp_factory_fake",
                    "object": "response",
                    "created_at": int(time.time()),
                    "model": model,
                    "status": "completed",
                    "error": None,
                    "incomplete_details": None,
                    "instructions": None,
                    "metadata": {},
                    "parallel_tool_calls": False,
                    "tool_choice": "auto",
                    "tools": [],
                    "output": [
                        {
                            "type": "message",
                            "id": "msg_factory_fake",
                            "role": "assistant",
                            "status": "completed",
                            "content": [
                                {"type": "output_text", "text": text, "annotations": []}
                            ],
                        }
                    ],
                },
            )
        elif path == "/v1/images/generations":
            n = max(1, min(int(body.get("n") or 1), 4))
            self._record(
                {
                    "endpoint": "images.generate",
                    "model": body.get("model"),
                    "n": n,
                    "size": body.get("size"),
                    "quality": body.get("quality"),
                    "background": body.get("background"),
                    "output_format": body.get("output_format"),
                    "prompt": str(body.get("prompt", ""))[:500],
                }
            )
            data = [
                {"b64_json": base64.b64encode(_synthetic_png(i)).decode("ascii")}
                for i in range(n)
            ]
            self._send(200, {"created": int(time.time()), "data": data})
        else:
            self._send(404, {"error": {"message": "not found", "type": "invalid_request_error"}})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8090)
    args = parser.parse_args()
    print(f"fake-openai on {args.port}", flush=True)
    ThreadingHTTPServer((args.host, args.port), _Handler).serve_forever()


if __name__ == "__main__":
    main()
