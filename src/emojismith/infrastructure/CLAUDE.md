# CLAUDE.md - Infrastructure Layer Guidelines

## Inheritance
- **Extends:** /CLAUDE.md (root)
- **Overrides:** None (CRITICAL RULES cannot be overridden)
- **Scope:** All files within `src/emojismith/infrastructure/` and subdirectories

## Rules

**Context:** This document provides guidelines for working with external services and adapters in the infrastructure layer (GCP + Slack + AI providers). Read this when implementing integrations, clients, or runtime wiring.

## Infrastructure Layer Responsibilities

The infrastructure layer handles:
- GCP integrations (Cloud Run runtime, Pub/Sub queue, Secret Manager configuration)
- External API clients (Slack, OpenAI, Google Gemini)
- Repository implementations (implementing domain/application protocols)
- Configuration wiring and environment-specific adapters
- Logging and monitoring concerns (structured logs, correlation IDs)

## Key Principles

1. **Implement Domain Interfaces**: Infrastructure implements protocols defined in domain/shared.
2. **Dependency Injection**: Inject external clients; avoid hard-coded singletons.
3. **Keep Business Logic Out**: Domain rules belong in domain/application, not adapters.
4. **Translate Errors**: Convert external exceptions into domain/application errors.
5. **Minimize `os.environ` Reads**: Prefer reading env vars in composition roots (e.g., `create_*` factories) and passing values in.

## Cloud Run Apps (Production Entry Points)

- Webhook service: `src/emojismith/infrastructure/gcp/webhook_app.py`
- Worker service: `src/emojismith/infrastructure/gcp/worker_app.py`
- Pub/Sub adapter: `src/emojismith/infrastructure/gcp/pubsub_job_queue.py`

See `README.md` for the deployed architecture.

## External Service Clients (Example Pattern)

```python
from slack_sdk.web.async_client import AsyncWebClient


class SlackAPIRepository:
    def __init__(self, client: AsyncWebClient) -> None:
        self._client = client  # injected dependency

    async def post_message(self, channel: str, text: str) -> None:
        await self._client.chat_postMessage(channel=channel, text=text)
```

Guidance:
- Keep adapters thin and focused on I/O + translation.
- Prefer returning simple primitives/DTOs rather than leaking provider-specific objects.

## Testing

- Mock external services (Slack API client, OpenAI client, `google.cloud.pubsub_v1.PublisherClient`).
- Avoid network calls in unit tests.
- Prefer behavior tests (inputs → outputs) over asserting internal calls.

For GCP-specific notes, also read `src/emojismith/infrastructure/gcp/CLAUDE.md`.

