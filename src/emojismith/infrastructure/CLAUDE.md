# CLAUDE.md - Infrastructure Layer Guidelines

## Inheritance
- **Extends:** /CLAUDE.md (root)
- **Overrides:** None (CRITICAL RULES cannot be overridden)
- **Scope:** All files within infrastructure directory and subdirectories

## Rules

**Context:** This document provides guidelines for working with GCP services, external APIs, and implementing repository patterns in the infrastructure layer. Read this when implementing integrations with external systems.

## Infrastructure Layer Responsibilities

The infrastructure layer handles:
- GCP service integration (Cloud Run, Pub/Sub, Secret Manager)
- External API clients (Slack, OpenAI, Google Gemini)
- Repository implementations
- Configuration management
- Logging and monitoring

## Key Principles

1. **Implement Domain Interfaces**: Infrastructure implements protocols defined in domain
2. **Handle External Complexity**: Shield domain from external service details
3. **Error Handling**: Transform external errors into domain exceptions
4. **Configuration**: Manage environment-specific settings

## GCP Architecture

### Dual Cloud Run Pattern
```
Slack → Webhook Cloud Run (< 3s) → Pub/Sub → Worker Cloud Run (async)
```

- **Webhook Service**: Public, responds within Slack's 3-second timeout
- **Worker Service**: Private, handles time-consuming image generation
- **Pub/Sub**: Provides buffering, retry logic, and dead-letter handling

## External Service Clients

### Slack Client Implementation
```python
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError

class SlackService:
    """Slack API service implementation."""

    def __init__(self, token: str):
        self._client = AsyncWebClient(token=token)

    async def post_message(
        self,
        channel: str,
        text: str,
        blocks: Optional[List[dict]] = None
    ) -> str:
        """Post message to Slack channel."""
        try:
            response = await self._client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks or []
            )
            return response["ts"]
        except SlackApiError as e:
            if e.response["error"] == "channel_not_found":
                raise ChannelNotFoundError(channel)
            raise ExternalServiceError(f"Slack API error: {e}")
```

### OpenAI Client Wrapper
```python
from openai import AsyncOpenAI

class OpenAIService:
    """OpenAI API service implementation."""

    def __init__(self, api_key: str):
        self._client = AsyncOpenAI(api_key=api_key)

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard"
    ) -> str:
        """Generate image and return URL."""
        try:
            response = await self._client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )
            return response.data[0].url
        except Exception as e:
            raise ImageGenerationError(f"Failed to generate image: {e}")
```

## Cloud Run Handler Patterns

### Webhook Handler (Fast Response)
```python
# src/emojismith/infrastructure/gcp/webhook_app.py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/slack/events")
async def slack_events(request: Request) -> dict:
    """Handle Slack webhook with <3s response time."""
    body = await request.body()
    headers = dict(request.headers)
    
    # Quick validation, queue for async processing
    return await webhook_handler.handle_event(body, headers)
```

### Worker Handler (Async Processing)
```python
# src/emojismith/infrastructure/gcp/worker_app.py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/process")
async def process_job(request: Request) -> dict:
    """Process emoji generation from Pub/Sub push."""
    # Full application processing
    message = await parse_pubsub_message(request)
    await app.process_emoji_request(message)
    return {"status": "ok"}
```

## Configuration Management

### Environment-Based Config
```python
import os

def get_config() -> dict:
    """Get configuration from environment."""
    return {
        "slack_token": os.environ.get("SLACK_BOT_TOKEN"),
        "slack_signing_secret": os.environ.get("SLACK_SIGNING_SECRET"),
        "openai_api_key": os.environ.get("OPENAI_API_KEY"),
        "google_api_key": os.environ.get("GOOGLE_API_KEY"),
        "pubsub_project": os.environ.get("PUBSUB_PROJECT"),
        "pubsub_topic": os.environ.get("PUBSUB_TOPIC"),
    }
```

### Secret Manager Integration
On Cloud Run, secrets are injected as environment variables directly from Secret Manager.
No runtime secret-fetching is needed - just read from `os.environ`.

## Error Handling Patterns

### Retry with Exponential Backoff
```python
from tenacity import retry, stop_after_attempt, wait_exponential

class ResilientService:
    """Service with retry logic."""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10)
    )
    async def call_external_api(self, data: dict) -> dict:
        """Call external API with retries."""
        response = await self._client.post("/api/endpoint", json=data)
        if response.status_code >= 500:
            raise TemporaryError("Server error")
        return response.json()
```

## Testing Infrastructure

### Mocking GCP Services
```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.fixture
def mock_pubsub_client():
    """Create mock Pub/Sub client."""
    client = Mock()
    client.publish = Mock(return_value=Mock(result=lambda: "message-id"))
    return client

@pytest.mark.asyncio
async def test_job_queue_publish(mock_pubsub_client):
    """Test Pub/Sub job queue publishing."""
    queue = PubSubJobQueue(client=mock_pubsub_client)
    await queue.enqueue({"type": "emoji_generation", "data": {}})
    mock_pubsub_client.publish.assert_called_once()
```

## Quick Reference

**Before implementing infrastructure code, verify:**
- [ ] Implementing domain interfaces (protocols)
- [ ] Proper error handling and transformation
- [ ] Configuration through environment variables
- [ ] Appropriate logging and monitoring
- [ ] Unit tests with mocked external services
- [ ] Retry logic for transient failures

**GCP-specific considerations:**
- Secrets are injected as environment variables by Cloud Run
- Worker Cloud Run should only be invokable by Pub/Sub
- Use structured logging for Cloud Logging integration
