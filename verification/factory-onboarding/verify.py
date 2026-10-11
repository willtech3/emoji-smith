"""Functional verifier for emoji-smith (Slack bot: webhook API + Pub/Sub worker).

Exercises real behaviour with synthetic data and writes
$FACTORY_EVIDENCE_DIR/verification-result.json {status, checks:[{id,status,observation}]}.

* HTTP checks hit the unmodified production webhook/worker apps started by start.sh.
* Slack requests, including URL verification, are HMAC-signed with a signing secret
  generated inside the sandbox. Only the gating bypass probe and the rejection
  check deliberately send unsigned or badly signed requests.
* Pub/Sub publishing reaches fake_pubsub.py through PUBSUB_EMULATOR_HOST.
* OpenAI calls reach fake_openai.py through OPENAI_BASE_URL.
* Slack Web API calls (views.open/update, file upload) cannot be redirected without
  code changes, so those two in-process checks use recording repositories that
  implement the application's own Slack protocols. Nothing contacts slack.com.

`--seed` only resets the fakes and writes the synthetic workspace fixture.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

STATE = Path(os.environ.get("FACTORY_STATE", "/tmp/emoji-smith-factory"))
WEBHOOK = "http://127.0.0.1:8080"
WORKER = "http://127.0.0.1:8081"
PUBSUB_HTTP = "http://127.0.0.1:8086"
OPENAI_HTTP = "http://127.0.0.1:8090"
FAKE_MARKER = "FACTORY-FAKE-ENHANCED"

SYNTHETIC = {
    "team_id": "T0FACTORY1",
    "channel_id": "C0FACTORY1",
    "user_id": "U0FACTORY1",
    "author_id": "U0AUTHOR01",
    "message_ts": "1700000000.000100",
    "message_text": "Synthetic team update: release v1.2 shipped to staging",
    "description": "a cheerful rocket giving a thumbs up",
}

_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))
CHECKS: list[dict[str, str]] = []
DETAILS: dict[str, Any] = {}
PUBLISHED_JOB: dict[str, Any] = {}


# --------------------------------------------------------------------------- helpers
def http(
    method: str,
    url: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 30,
) -> tuple[int, bytes]:
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with _OPENER.open(req, timeout=timeout) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def as_json(raw: bytes) -> Any:
    try:
        return json.loads(raw or b"null")
    except json.JSONDecodeError:
        return {"_raw": raw[:300].decode("utf-8", "replace")}


def published_messages() -> list[dict[str, Any]]:
    status, raw = http("GET", f"{PUBSUB_HTTP}/messages")
    if status != 200:
        raise RuntimeError(f"fake-pubsub /messages returned {status}")
    out = []
    for msg in as_json(raw)["messages"]:
        decoded = dict(msg)
        try:
            decoded["job"] = json.loads(base64.b64decode(msg["data_b64"]))
        except Exception:  # noqa: BLE001
            decoded["job"] = None
        out.append(decoded)
    return out


def jobs_named(name: str) -> list[dict[str, Any]]:
    return [m for m in published_messages() if (m.get("job") or {}).get("emoji_name") == name]


def signing_secret() -> str:
    secret = os.environ.get("SLACK_SIGNING_SECRET", "")
    if not secret:
        raise RuntimeError("SLACK_SIGNING_SECRET not generated (start.sh must run first)")
    return secret


def sign(body: bytes, *, ts: int | None = None, secret: str | None = None) -> dict[str, str]:
    stamp = str(ts if ts is not None else int(time.time()))
    key = (secret if secret is not None else signing_secret()).encode()
    digest = hmac.new(key, b"v0:" + stamp.encode() + b":" + body, hashlib.sha256).hexdigest()
    return {"X-Slack-Request-Timestamp": stamp, "X-Slack-Signature": f"v0={digest}"}


def form_body(payload: dict[str, Any]) -> bytes:
    return b"payload=" + urllib.parse.quote(json.dumps(payload), safe="").encode()


FORM = {"Content-Type": "application/x-www-form-urlencoded"}


def private_metadata() -> str:
    return json.dumps(
        {
            "message_text": SYNTHETIC["message_text"],
            "user_id": SYNTHETIC["user_id"],
            "channel_id": SYNTHETIC["channel_id"],
            "timestamp": SYNTHETIC["message_ts"],
            "team_id": SYNTHETIC["team_id"],
            "show_advanced": False,
        }
    )


def view_submission(description: str, emoji_name: str | None) -> dict[str, Any]:
    values: dict[str, Any] = {
        "emoji_description": {"description": {"type": "plain_text_input", "value": description}},
        "image_provider_block": {
            "image_provider_select": {"type": "static_select", "selected_option": {"value": "openai"}}
        },
    }
    if emoji_name is not None:
        values["emoji_name"] = {"name": {"type": "plain_text_input", "value": emoji_name}}
    return {
        "type": "view_submission",
        "team": {"id": SYNTHETIC["team_id"]},
        "user": {"id": SYNTHETIC["user_id"]},
        "view": {
            "id": "V0FACTORY1",
            "callback_id": "emoji_creation_modal",
            "private_metadata": private_metadata(),
            "state": {"values": values},
        },
    }


def run_check(check_id: str, fn: Any) -> None:
    try:
        ok, observation = fn()
    except Exception as exc:  # noqa: BLE001
        ok, observation = False, f"exception: {type(exc).__name__}: {exc}"
    CHECKS.append(
        {"id": check_id, "status": "passed" if ok else "failed", "observation": observation[:1800]}
    )
    print(f"[{'PASS' if ok else 'FAIL'}] {check_id}: {observation[:300]}", flush=True)


# ---------------------------------------------------------------------------- checks
def check_webhook_health() -> tuple[bool, str]:
    status, raw = http("GET", f"{WEBHOOK}/health")
    body = as_json(raw)
    ok = status == 200 and body == {"status": "healthy", "service": "webhook"}
    return ok, f"GET /health -> {status} {body}"


def check_url_verification() -> tuple[bool, str]:
    """Slack URL verification is authenticated like every other request (PR 415),
    so the challenge is HMAC-signed with the sandbox-generated signing secret."""
    before = len(published_messages())
    challenge = f"factory-challenge-{secrets.token_hex(8)}"
    body = json.dumps(
        {"type": "url_verification", "challenge": challenge}, separators=(",", ":")
    ).encode()
    status, raw = http(
        "POST",
        f"{WEBHOOK}/slack/events",
        body,
        {"Content-Type": "application/json", **sign(body)},
    )
    got = as_json(raw)
    time.sleep(1)
    after = len(published_messages())
    echoed = got == {"challenge": challenge}
    ok = status == 200 and echoed and after == before
    return ok, (
        f"signed POST /slack/events url_verification -> {status}, challenge echoed={echoed}; "
        f"published messages before={before} after={after}"
    )


def check_submission_validation() -> tuple[bool, str]:
    before = len(published_messages())
    results = []
    cases = [
        ("empty-description", view_submission("   ", None), "emoji_description"),
        ("invalid-name", view_submission(SYNTHETIC["description"], "Bad Name!"), "emoji_name"),
    ]
    ok = True
    for label, payload, block in cases:
        body = form_body(payload)
        status, raw = http("POST", f"{WEBHOOK}/slack/interactive", body, {**FORM, **sign(body)})
        got = as_json(raw)
        case_ok = (
            status == 200
            and got.get("response_action") == "errors"
            and block in (got.get("errors") or {})
        )
        ok = ok and case_ok
        results.append(f"{label}: {status} response_action={got.get('response_action')} error_blocks={list((got.get('errors') or {}).keys())}")
    time.sleep(1.5)
    after = len(published_messages())
    ok = ok and after == before
    return ok, "; ".join(results) + f"; published messages before={before} after={after}"


def check_rejects_unauthenticated() -> tuple[bool, str]:
    name = f"factory_reject_{secrets.token_hex(4)}"
    body = form_body(view_submission(SYNTHETIC["description"], name))
    tampered = form_body(view_submission(SYNTHETIC["description"] + " now", name))
    cases = {
        "missing-signature": (body, {}),
        "wrong-secret": (body, sign(body, secret=secrets.token_hex(32))),
        "tampered-body": (tampered, sign(body)),
        "stale-timestamp": (body, sign(body, ts=int(time.time()) - 600)),
    }
    statuses = {}
    for label, (payload, headers) in cases.items():
        status, _ = http("POST", f"{WEBHOOK}/slack/interactive", payload, {**FORM, **headers})
        statuses[label] = status
    time.sleep(2)
    leaked = jobs_named(name)
    ok = all(s >= 400 for s in statuses.values()) and not leaked
    return ok, (
        f"statuses={statuses} (any non-2xx accepted; the app has no handler mapping "
        f"UnauthorizedError, so 500 is expected rather than 401); jobs published={len(leaked)}"
    )


def check_signed_submission() -> tuple[bool, str]:
    name = f"factory_rocket_{secrets.token_hex(4)}"
    body = form_body(view_submission(SYNTHETIC["description"], name))
    status, raw = http(
        "POST", f"{WEBHOOK}/slack/interactive", body, {**FORM, **sign(body)}, timeout=90
    )
    got = as_json(raw)
    matches: list[dict[str, Any]] = []
    for _ in range(30):
        matches = jobs_named(name)
        if matches:
            break
        time.sleep(0.5)
    expected_topic = f"projects/{os.environ['PUBSUB_PROJECT']}/topics/{os.environ['PUBSUB_TOPIC']}"
    if not matches:
        return False, f"POST /slack/interactive -> {status} {got}; no job named {name} reached fake Pub/Sub"
    msg = matches[0]
    job = msg["job"]
    PUBLISHED_JOB.update(job)
    DETAILS["published_job"] = job
    problems = []
    if status != 200 or got != {"response_action": "clear"}:
        problems.append(f"response {status} {got}")
    if msg["topic"] != expected_topic:
        problems.append(f"topic {msg['topic']}")
    for key, want in (
        ("user_description", SYNTHETIC["description"]),
        ("channel_id", SYNTHETIC["channel_id"]),
        ("user_id", SYNTHETIC["user_id"]),
        ("team_id", SYNTHETIC["team_id"]),
        ("timestamp", SYNTHETIC["message_ts"]),
        ("message_text", SYNTHETIC["message_text"]),
        ("image_provider", "openai"),
    ):
        if job.get(key) != want:
            problems.append(f"{key}={job.get(key)!r}")
    if not job.get("job_id") or not job.get("trace_id"):
        problems.append("missing job_id/trace_id")
    return not problems, (
        f"POST /slack/interactive -> {status} {got}; published to {msg['topic']} "
        f"(message_id {msg['message_id']}) job emoji_name={job.get('emoji_name')} "
        f"provider={job.get('image_provider')} channel={job.get('channel_id')}"
        + (f"; problems: {problems}" if problems else "")
    )


def _bypass_variants() -> dict[str, tuple[bytes, dict[str, str], str]]:
    """UNSIGNED bodies that disguise a view_submission as Slack URL verification.

    Each variant carries a unique emoji_name so any leaked job is attributable.
    Returns {variant: (body, headers, emoji_name)}; no Slack signature headers.
    """
    variants: dict[str, tuple[bytes, dict[str, str], str]] = {}
    json_headers = {"Content-Type": "application/json"}

    def submission(label: str) -> tuple[bytes, str]:
        # <= 32 chars of [a-z0-9_] so a leaked submission would pass name validation.
        name = f"factory_bp_{label}_{secrets.token_hex(3)}"
        raw = json.dumps(view_submission(SYNTHETIC["description"], name), separators=(",", ":"))
        return raw.encode(), name  # starts with {"type":"view_submission"

    # 1. duplicate-key: json.loads keeps the last "type" -> view_submission.
    sub, name = submission("dup")
    variants["duplicate-key"] = (b'{"type":"url_verification",' + sub[1:], json_headers, name)

    # 2. escaped-key: second key is "t\u0079pe", which decodes to "type".
    sub, name = submission("esc")
    sub = sub.replace(b'"type"', b'"t\\u0079pe"', 1)
    variants["escaped-key"] = (b'{"type":"url_verification",' + sub[1:], json_headers, name)

    # 3. malformed-prefix / form-fallback: invalid JSON that starts like URL
    #    verification, so the processor falls back to parse_qs and reads payload=.
    sub, name = submission("form")
    variants["malformed-prefix-form-fallback"] = (
        b'{"type":"url_verification"&payload=' + urllib.parse.quote_from_bytes(sub).encode(),
        FORM,
        name,
    )

    # 4. plain unsigned URL verification: must not echo the challenge any more.
    variants["unsigned-url-verification"] = (
        json.dumps(
            {"type": "url_verification", "challenge": "factory-unsigned-challenge"},
            separators=(",", ":"),
        ).encode(),
        json_headers,
        "",
    )
    return variants


def check_url_verification_bypass() -> tuple[bool, str]:
    """Gating security probe (url-verification-bypass answer; fix merged in PR 415).

    Every UNSIGNED disguise variant is sent to BOTH production webhook routes.
    Passes only if every response is non-2xx, no challenge is echoed, and the fake
    Pub/Sub receives no message at all (total count unchanged and no job carrying
    any probe emoji_name). Application code is never changed by this recipe.
    """
    before = len(published_messages())
    variants = _bypass_variants()
    results: dict[str, dict[str, Any]] = {}
    failures: list[str] = []
    for label, (body, headers, _name) in variants.items():
        for path in ("/slack/events", "/slack/interactive"):
            status, raw = http("POST", f"{WEBHOOK}{path}", body, dict(headers))
            got = as_json(raw)
            key = f"{label} {path}"
            results[key] = {"status": status, "body": got}
            if 200 <= status < 300:
                failures.append(f"{key} accepted with {status}")
            if isinstance(got, dict) and "challenge" in got:
                failures.append(f"{key} echoed challenge")
    time.sleep(2)
    msgs = published_messages()
    names = {n for (_b, _h, n) in variants.values() if n}
    leaked = [m for m in msgs if (m.get("job") or {}).get("emoji_name") in names]
    new_count = len(msgs) - before
    if leaked or new_count:
        failures.append(
            f"queued jobs: {new_count} new message(s), {len(leaked)} carrying probe names "
            f"{sorted({(m.get('job') or {}).get('emoji_name') for m in leaked})}"
        )
    DETAILS["url_verification_bypass_probe"] = {
        "variants": {k: v[0][:120].decode("utf-8", "replace") for k, v in variants.items()},
        "responses": results,
        "messages_before": before,
        "messages_after": len(msgs),
        "leaked_jobs": [m.get("job") for m in leaked],
    }
    statuses = ", ".join(f"{k} -> {v['status']}" for k, v in results.items())
    if failures:
        return False, (
            "UNSIGNED DISGUISED REQUEST NOT FULLY REJECTED: "
            + "; ".join(failures)
            + f". Statuses: {statuses}. Details in verification-details.json."
        )
    return True, (
        f"all {len(results)} unsigned variant/route requests rejected (non-2xx, no challenge "
        f"echoed): {statuses}; queued jobs=0 (messages before={before} after={len(msgs)})"
    )


class RecordingSlackRepo:
    """Implements shared.domain.repositories.SlackRepository; records instead of calling Slack."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def open_modal(self, trigger_id: str, view: dict[str, Any]) -> None:
        self.calls.append(("open_modal", {"trigger_id": trigger_id, "view": view}))

    async def update_modal(self, view_id: str, view: dict[str, Any]) -> None:
        self.calls.append(("update_modal", {"view_id": view_id, "view": view}))

    async def upload_emoji(self, name: str, image_data: bytes) -> bool:
        self.calls.append(("upload_emoji", {"name": name, "bytes": len(image_data)}))
        return True

    async def add_emoji_reaction(self, emoji_name: str, channel_id: str, timestamp: str) -> None:
        self.calls.append(("add_emoji_reaction", {"emoji_name": emoji_name}))


class RecordingQueue:
    def __init__(self) -> None:
        self.jobs: list[Any] = []

    async def enqueue_job(self, job: Any) -> str:
        self.jobs.append(job)
        return f"local-{len(self.jobs)}"


def check_modal_flow() -> tuple[bool, str]:
    from emojismith.application.handlers.slack_webhook_handler import (
        SlackWebhookHandler,
        UnauthorizedError,
        WebhookEventProcessor,
    )
    from emojismith.domain.services.webhook_security_service import WebhookSecurityService
    from emojismith.infrastructure.security.slack_signature_validator import (
        SlackSignatureValidator,
    )

    slack = RecordingSlackRepo()
    queue = RecordingQueue()
    handler = SlackWebhookHandler(
        security_service=WebhookSecurityService(
            SlackSignatureValidator(signing_secret=signing_secret())
        ),
        event_processor=WebhookEventProcessor(slack_repo=slack, job_queue=queue, google_enabled=True),
    )

    def lower(h: dict[str, str]) -> dict[str, str]:
        return {k.lower(): v for k, v in h.items()}

    action = {
        "type": "message_action",
        "callback_id": "create_emoji_reaction",
        "trigger_id": "1337.factory.trigger",
        "team": {"id": SYNTHETIC["team_id"]},
        "channel": {"id": SYNTHETIC["channel_id"]},
        "user": {"id": SYNTHETIC["user_id"]},
        "message": {
            "type": "message",
            "text": SYNTHETIC["message_text"],
            "user": SYNTHETIC["author_id"],
            "ts": SYNTHETIC["message_ts"],
        },
    }

    async def flow() -> tuple[bool, str]:
        notes = []
        body = form_body(action)
        unsigned_rejected = False
        try:
            await handler.handle_event(body, {})
        except UnauthorizedError:
            unsigned_rejected = True
        notes.append(f"unsigned message_action rejected={unsigned_rejected}, slack calls={len(slack.calls)}")
        if slack.calls:
            return False, "; ".join(notes)

        result = await handler.handle_event(body, lower(sign(body)))
        opened = [c for c in slack.calls if c[0] == "open_modal"]
        if result != {"status": "ok"} or len(opened) != 1:
            return False, f"signed message_action -> {result}, open_modal calls={len(opened)}"
        view = opened[0][1]["view"]
        meta = json.loads(view.get("private_metadata", "{}"))
        blocks = [b.get("block_id") for b in view.get("blocks", []) if b.get("block_id")]
        collapsed_ok = (
            opened[0][1]["trigger_id"] == action["trigger_id"]
            and view.get("callback_id") == "emoji_creation_modal"
            and meta.get("message_text") == SYNTHETIC["message_text"]
            and meta.get("user_id") == SYNTHETIC["user_id"]
            and meta.get("channel_id") == SYNTHETIC["channel_id"]
            and "emoji_description" in blocks
            and "quality_block" not in blocks
        )
        notes.append(f"open_modal callback_id={view.get('callback_id')} blocks={blocks} metadata_ok={collapsed_ok}")

        toggle = {
            "type": "block_actions",
            "trigger_id": "1338.factory.trigger",
            "user": {"id": SYNTHETIC["user_id"]},
            "team": {"id": SYNTHETIC["team_id"]},
            "actions": [{"type": "button", "action_id": "toggle_style_options", "value": "expand"}],
            "view": {"id": "V0FACTORY2", "private_metadata": view["private_metadata"]},
        }
        tbody = form_body(toggle)
        await handler.handle_event(tbody, lower(sign(tbody)))
        updated = [c for c in slack.calls if c[0] == "update_modal"]
        expanded_ok = False
        if len(updated) == 1:
            uview = updated[0][1]["view"]
            ublocks = [b.get("block_id") for b in uview.get("blocks", []) if b.get("block_id")]
            umeta = json.loads(uview.get("private_metadata", "{}"))
            expanded_ok = (
                updated[0][1]["view_id"] == "V0FACTORY2"
                and "quality_block" in ublocks
                and "emoji_name" in ublocks
                and umeta.get("show_advanced") is True
                and umeta.get("channel_id") == SYNTHETIC["channel_id"]
            )
            notes.append(f"update_modal view_id={updated[0][1]['view_id']} blocks={ublocks}")
        notes.append(f"jobs enqueued during modal flow={len(queue.jobs)}")
        ok = unsigned_rejected and collapsed_ok and expanded_ok and not queue.jobs
        return ok, "; ".join(notes) + " (Slack views API replaced by recording repository)"

    return asyncio.run(flow())


def check_worker_push_validation() -> tuple[bool, str]:
    hs, hraw = http("GET", f"{WORKER}/health")
    s1, r1 = http("POST", f"{WORKER}/pubsub", b"{}", {"Content-Type": "application/json"})
    s2, r2 = http(
        "POST",
        f"{WORKER}/pubsub",
        json.dumps({"message": {"messageId": "factory-no-data"}}).encode(),
        {"Content-Type": "application/json"},
    )
    ok = hs == 200 and as_json(hraw) == {"status": "healthy"} and s1 == 400 and s2 == 400
    return ok, (
        f"GET /health -> {hs} {as_json(hraw)}; empty envelope -> {s1} {as_json(r1)}; "
        f"message without data -> {s2} {as_json(r2)}"
    )


class RecordingFileSharing:
    """Implements FileSharingRepository; records the share instead of uploading to Slack."""

    def __init__(self) -> None:
        self.shares: list[dict[str, Any]] = []

    async def share_emoji_file(
        self,
        emoji: Any,
        channel_id: str,
        preferences: Any,
        requester_user_id: str,
        original_message_ts: str | None = None,
        initial_comment: str | None = None,
        upload_instructions: str | None = None,
    ) -> Any:
        from emojismith.domain.repositories.file_sharing_repository import FileSharingResult

        self.shares.append(
            {
                "name": emoji.name,
                "format": emoji.format,
                "image_data": emoji.image_data,
                "channel_id": channel_id,
                "requester_user_id": requester_user_id,
                "original_message_ts": original_message_ts,
                "initial_comment": initial_comment,
                "upload_instructions": upload_instructions,
            }
        )
        return FileSharingResult(
            success=True, thread_ts="1700000000.000200", file_url="synthetic://factory/file"
        )


def check_worker_pipeline() -> tuple[bool, str]:
    if not PUBLISHED_JOB:
        return False, "no job was published by signed-submission-enqueues-job; nothing to process"

    from openai import AsyncOpenAI
    from PIL import Image

    from emojismith.application.services.emoji_service import EmojiCreationService
    from emojismith.application.use_cases.build_prompt_use_case import BuildPromptUseCase
    from emojismith.domain.services.emoji_instruction_service import EmojiInstructionService
    from emojismith.domain.services.emoji_sharing_service import (
        EmojiSharingService,
        WorkspaceType,
    )
    from emojismith.domain.services.emoji_validation_service import EmojiValidationService
    from emojismith.domain.services.style_template_manager import StyleTemplateManager
    from emojismith.infrastructure.factories import ImageGeneratorFactory
    from emojismith.infrastructure.image.pil_image_validator import PILImageValidator
    from emojismith.infrastructure.image.processing import PillowImageProcessor
    from emojismith.infrastructure.openai.openai_api import (
        OPENAI_IMAGE_MODEL,
        OpenAIAPIRepository,
    )
    from emojismith.infrastructure.repositories.style_template_config_repository import (
        StyleTemplateConfigRepository,
    )
    from shared.domain.dtos import EmojiGenerationJobDto

    http("POST", f"{OPENAI_HTTP}/reset")
    api_key = os.environ["OPENAI_API_KEY"]  # sandbox-generated synthetic value
    slack = RecordingSlackRepo()
    sharing = RecordingFileSharing()

    async def run() -> None:
        # Mirrors emojismith.app.create_worker_emoji_service; only Slack adapters differ.
        openai_repo = OpenAIAPIRepository(
            AsyncOpenAI(api_key=api_key), model=os.getenv("OPENAI_CHAT_MODEL", "gpt-5")
        )
        service = EmojiCreationService(
            slack_repo=slack,
            build_prompt_use_case=BuildPromptUseCase(prompt_enhancer=openai_repo),
            image_generator_factory=ImageGeneratorFactory(openai_api_key=api_key),
            image_processor=PillowImageProcessor(),
            emoji_validator=EmojiValidationService(PILImageValidator()),
            style_template_manager=StyleTemplateManager(StyleTemplateConfigRepository()),
            job_queue=None,
            file_sharing_repo=sharing,
            sharing_service=EmojiSharingService(workspace_type=WorkspaceType.STANDARD),
            instruction_service=EmojiInstructionService(),
        )
        await service.process_emoji_generation_job(EmojiGenerationJobDto(**PUBLISHED_JOB))

    asyncio.run(run())

    status, raw = http("GET", f"{OPENAI_HTTP}/requests")
    reqs = as_json(raw).get("requests", []) if status == 200 else []
    endpoints = [r.get("endpoint") for r in reqs]
    responses = [r for r in reqs if r.get("endpoint") == "responses.create"]
    images = [r for r in reqs if r.get("endpoint") == "images.generate"]
    problems = []
    if len(responses) != 1:
        problems.append(f"responses.create calls={len(responses)}")
    if len(images) != 1:
        problems.append(f"images.generate calls={len(images)}")
    elif not (
        images[0].get("model") == OPENAI_IMAGE_MODEL
        and images[0].get("n") == 1
        and images[0].get("size") == "1024x1024"
        and FAKE_MARKER in (images[0].get("prompt") or "")
    ):
        problems.append(f"unexpected image request {images[0]}")
    if not all(r.get("auth_header_present") for r in reqs):
        problems.append("OpenAI request without Authorization header")

    share_note = "no share recorded"
    if len(sharing.shares) != 1:
        problems.append(f"file shares={len(sharing.shares)}")
    else:
        share = sharing.shares[0]
        with Image.open(BytesIO(share["image_data"])) as img:
            fmt, size, mode = img.format, img.size, img.mode
        expected_name = PUBLISHED_JOB["emoji_name"].replace(" ", "_").lower()[:32]
        share_note = (
            f"shared {share['name']} {fmt} {size[0]}x{size[1]} {mode} "
            f"{len(share['image_data'])} bytes to {share['channel_id']} for "
            f"{share['requester_user_id']}, thread ts {share['original_message_ts']}, "
            f"initial_comment={share['initial_comment']!r}"
        )
        if not (
            fmt == "PNG"
            and size == (128, 128)
            and len(share["image_data"]) < 64 * 1024
            and share["name"] == expected_name
            and share["channel_id"] == SYNTHETIC["channel_id"]
            and share["requester_user_id"] == SYNTHETIC["user_id"]
            and share["original_message_ts"] == SYNTHETIC["message_ts"]
            and share["initial_comment"]
            and f":{expected_name}:" in share["initial_comment"]
        ):
            problems.append("shared emoji did not match expectations")
    direct = [c for c in slack.calls if c[0] in ("upload_emoji", "add_emoji_reaction")]
    if direct:
        problems.append(f"unexpected direct Slack emoji calls {direct}")
    DETAILS["openai_requests"] = reqs
    return not problems, (
        f"fake OpenAI saw {endpoints}; {share_note}"
        + (f"; problems: {problems}" if problems else "")
        + " (Slack upload replaced by recording repository)"
    )


def check_ci_test_suite(evidence: Path) -> tuple[bool, str]:
    # Mirror CI's clean environment: drop every app/runtime variable this recipe sets.
    app_vars = {"ENVIRONMENT", "LOG_LEVEL", "TRACING_ENABLED", "METRICS_ENABLED", "TRACE_SAMPLE_RATE"}
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in app_vars and not k.startswith(("SLACK_", "OPENAI_", "GOOGLE_", "PUBSUB_"))
    }
    proc = subprocess.run(  # noqa: S603
        [str(ROOT / ".venv" / "bin" / "python"), "-m", "pytest", "tests/", "-q"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=1200,
        check=False,
    )
    output = proc.stdout + "\n" + proc.stderr
    (evidence / "pytest-output.txt").write_text(output, encoding="utf-8")
    lines = [ln for ln in proc.stdout.strip().splitlines() if ln.strip()]
    summary = lines[-1] if lines else "(no output)"
    return proc.returncode == 0, f"pytest tests/ -q exit={proc.returncode}; {summary} (full log: pytest-output.txt)"


# ------------------------------------------------------------------------------ main
def seed() -> int:
    for url in (f"{PUBSUB_HTTP}/reset", f"{OPENAI_HTTP}/reset"):
        status, _ = http("POST", url)
        if status != 200:
            print(f"reset failed for {url}: {status}", file=sys.stderr)
            return 1
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "synthetic-workspace.json").write_text(json.dumps(SYNTHETIC, indent=2), encoding="utf-8")
    print("fakes reset; synthetic workspace fixture written")
    return 0


def main() -> int:
    if "--seed" in sys.argv:
        return seed()
    evidence_env = os.environ.get("FACTORY_EVIDENCE_DIR")
    evidence = Path(evidence_env) if evidence_env else STATE / "evidence"
    if not evidence_env:
        print("FACTORY_EVIDENCE_DIR not set; writing to", evidence, file=sys.stderr)
    evidence.mkdir(parents=True, exist_ok=True)

    run_check("webhook-health", check_webhook_health)
    run_check("slack-url-verification", check_url_verification)
    run_check("submission-validation-errors", check_submission_validation)
    run_check("rejects-unauthenticated-requests", check_rejects_unauthenticated)
    run_check("signed-submission-enqueues-job", check_signed_submission)
    run_check("url-verification-bypass-probe", check_url_verification_bypass)
    run_check("modal-flow", check_modal_flow)
    run_check("worker-push-validation", check_worker_push_validation)
    run_check("worker-pipeline", check_worker_pipeline)
    run_check("ci-test-suite", lambda: check_ci_test_suite(evidence))

    overall = "passed" if all(c["status"] == "passed" for c in CHECKS) else "failed"
    (evidence / "verification-result.json").write_text(
        json.dumps({"status": overall, "checks": CHECKS}, indent=2), encoding="utf-8"
    )
    (evidence / "verification-details.json").write_text(
        json.dumps(DETAILS, indent=2, default=str), encoding="utf-8"
    )
    print(f"overall: {overall}")
    return 0 if overall == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
