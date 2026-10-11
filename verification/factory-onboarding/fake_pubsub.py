"""In-sandbox Pub/Sub *publisher* fake for Factory onboarding verification.

Implements the real ``google.pubsub.v1.Publisher/Publish`` gRPC method so the
unmodified ``PubSubJobQueue`` (google-cloud-pubsub ``PublisherClient`` with
``PUBSUB_EMULATOR_HOST``) publishes to it with anonymous credentials.

This is NOT Google's Pub/Sub emulator: only Publish is implemented, topics are
accepted without being created, and there are no subscriptions or push delivery.
Recorded messages are exposed over plain HTTP (GET /messages, POST /reset).
"""

from __future__ import annotations

import argparse
import base64
import json
import threading
from concurrent import futures
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import grpc
from google.pubsub_v1 import PublishRequest, PublishResponse

_LOCK = threading.Lock()
_MESSAGES: list[dict[str, Any]] = []
_COUNTER = [0]


def _publish(request: PublishRequest, context: grpc.ServicerContext) -> PublishResponse:
    ids: list[str] = []
    with _LOCK:
        for msg in request.messages:
            _COUNTER[0] += 1
            message_id = f"factory-{_COUNTER[0]}"
            _MESSAGES.append(
                {
                    "topic": request.topic,
                    "message_id": message_id,
                    "data_b64": base64.b64encode(bytes(msg.data)).decode("ascii"),
                    "attributes": dict(msg.attributes),
                    "ordering_key": msg.ordering_key,
                }
            )
            ids.append(message_id)
    return PublishResponse(message_ids=ids)


class _HttpHandler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: Any) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health":
            self._send(200, {"status": "ok", "service": "fake-pubsub"})
        elif self.path == "/messages":
            with _LOCK:
                self._send(200, {"messages": list(_MESSAGES)})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/reset":
            with _LOCK:
                _MESSAGES.clear()
            self._send(200, {"status": "reset"})
        else:
            self._send(404, {"error": "not found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--grpc-port", type=int, default=8085)
    parser.add_argument("--http-port", type=int, default=8086)
    args = parser.parse_args()

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=8))
    handler = grpc.method_handlers_generic_handler(
        "google.pubsub.v1.Publisher",
        {
            "Publish": grpc.unary_unary_rpc_method_handler(
                _publish,
                request_deserializer=PublishRequest.deserialize,
                response_serializer=PublishResponse.serialize,
            )
        },
    )
    server.add_generic_rpc_handlers((handler,))
    if server.add_insecure_port(f"{args.host}:{args.grpc_port}") == 0:
        raise SystemExit(f"could not bind gRPC port {args.grpc_port}")
    server.start()
    print(f"fake-pubsub gRPC on {args.grpc_port}, HTTP on {args.http_port}", flush=True)

    ThreadingHTTPServer((args.host, args.http_port), _HttpHandler).serve_forever()


if __name__ == "__main__":
    main()
