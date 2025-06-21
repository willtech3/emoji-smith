# CLAUDE Infrastructure Guidelines for Emoji Smith

**Context:** This document should be loaded when working with AWS services, external APIs, or implementing repository patterns.

## Infrastructure Layer Responsibilities

The infrastructure layer handles:
- AWS service integration (Lambda, S3, SQS, Secrets Manager)
- External API clients (Slack, OpenAI)
- Repository implementations
- Configuration management
- Logging and monitoring

## Key Principles

1. **Implement Domain Interfaces**: Infrastructure implements protocols defined in domain
2. **Handle External Complexity**: Shield domain from external service details
3. **Error Handling**: Transform external errors into domain exceptions
4. **Configuration**: Manage environment-specific settings

## Repository Implementation Pattern

### DynamoDB Repository Example
```python
from typing import Optional, List
import boto3
from boto3.dynamodb.conditions import Key

from domain.entities.emoji_template import EmojiTemplate
from domain.repositories.emoji_template_repository import EmojiTemplateRepository

class DynamoDBEmojiTemplateRepository:
    """DynamoDB implementation of emoji template repository."""

    def __init__(self, table_name: str):
        self._table = boto3.resource('dynamodb').Table(table_name)

    async def get_by_id(self, template_id: str) -> Optional[EmojiTemplate]:
        """Retrieve template by ID."""
        try:
            response = self._table.get_item(Key={'id': template_id})

            if 'Item' not in response:
                return None

            return self._deserialize(response['Item'])
        except Exception as e:
            # Log error
            raise RepositoryError(f"Failed to retrieve template: {e}")

    async def save(self, template: EmojiTemplate) -> None:
        """Persist template."""
        try:
            self._table.put_item(Item=self._serialize(template))
        except Exception as e:
            raise RepositoryError(f"Failed to save template: {e}")

    def _serialize(self, template: EmojiTemplate) -> dict:
        """Convert domain entity to DynamoDB item."""
        return {
            'id': template.id,
            'name': template.name,
            'prompt_template': template.prompt_template,
            'created_at': template.created_at.isoformat(),
            'usage_count': template.usage_count
        }

    def _deserialize(self, item: dict) -> EmojiTemplate:
        """Convert DynamoDB item to domain entity."""
        return EmojiTemplate(
            id=item['id'],
            name=item['name'],
            prompt_template=item['prompt_template'],
            created_at=datetime.fromisoformat(item['created_at']),
            usage_count=item.get('usage_count', 0)
        )
```

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
from typing import Optional

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
                model="dall-e-3",
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )
            return response.data[0].url
        except Exception as e:
            raise ImageGenerationError(f"Failed to generate image: {e}")
```

## Lambda Handler Patterns

### Webhook Handler (Fast Response)
```python
# src/emojismith/infrastructure/aws/webhook_handler.py
import json
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

logger = Logger()

@logger.inject_lambda_context
async def handler(event: dict, context: LambdaContext) -> dict:
    """Handle Slack webhook with <3s response time."""
    try:
        # Quick validation
        body = json.loads(event["body"])

        if body.get("type") == "url_verification":
            return {
                "statusCode": 200,
                "body": json.dumps({"challenge": body["challenge"]})
            }

        # Queue for async processing
        await queue_message(body)

        # Quick response
        return {
            "statusCode": 200,
            "body": json.dumps({"status": "processing"})
        }
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return {"statusCode": 500, "body": "Internal error"}
```

### Worker Handler (Async Processing)
```python
# src/emojismith/infrastructure/aws/worker_handler.py
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.batch import process_partial_response

logger = Logger()

@logger.inject_lambda_context
@process_partial_response()
async def handler(event: dict, context: LambdaContext) -> dict:
    """Process emoji generation from SQS queue."""
    # Full application initialization
    app = await initialize_application()

    for record in event["Records"]:
        try:
            message = json.loads(record["body"])
            await app.process_emoji_request(message)
        except Exception as e:
            logger.error(f"Processing error: {e}")
            raise  # Let Lambda retry
```

## Configuration Management

### Environment-Based Config
```python
from pydantic import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings from environment."""

    # AWS
    dynamodb_table_name: str
    s3_bucket_name: str
    sqs_queue_url: str

    # External APIs
    slack_bot_token: str
    openai_api_key: str

    # App config
    emoji_generation_timeout: int = 30
    max_retries: int = 3

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

### Secrets Manager Integration
```python
import boto3
import json
from functools import lru_cache

class SecretsManager:
    """AWS Secrets Manager client."""

    def __init__(self):
        self._client = boto3.client('secretsmanager')

    @lru_cache(maxsize=32)
    def get_secret(self, secret_name: str) -> dict:
        """Retrieve and cache secret."""
        try:
            response = self._client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Failed to retrieve secret {secret_name}: {e}")
            raise
```

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

### Circuit Breaker Pattern
```python
from pybreaker import CircuitBreaker

class ProtectedService:
    """Service with circuit breaker."""

    def __init__(self):
        self._breaker = CircuitBreaker(
            fail_max=5,
            reset_timeout=60,
            exclude=[ValueError]  # Don't trip on client errors
        )

    @property
    def circuit_breaker(self):
        return self._breaker

    async def call_service(self, data: dict) -> dict:
        """Call service with circuit breaker protection."""
        return await self._breaker(self._unsafe_call)(data)
```

## Testing Infrastructure

### Mocking AWS Services
```python
import pytest
from moto import mock_dynamodb, mock_s3
import boto3

@pytest.fixture
@mock_dynamodb
def dynamodb_table():
    """Create mock DynamoDB table."""
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    table = dynamodb.create_table(
        TableName='test-table',
        KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
        AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
        BillingMode='PAY_PER_REQUEST'
    )

    return table

@pytest.mark.asyncio
async def test_repository_save(dynamodb_table):
    """Test DynamoDB repository save."""
    repo = DynamoDBEmojiTemplateRepository('test-table')
    template = EmojiTemplate(
        id="test-123",
        name="Test",
        prompt_template="test {message}",
        created_at=datetime.now()
    )

    await repo.save(template)

    # Verify in table
    item = dynamodb_table.get_item(Key={'id': 'test-123'})
    assert item['Item']['name'] == 'Test'
```

## Performance Optimization

### Connection Pooling
```python
from aiohttp import ClientSession, TCPConnector

class OptimizedHttpClient:
    """HTTP client with connection pooling."""

    def __init__(self):
        self._connector = TCPConnector(
            limit=100,
            limit_per_host=30,
            ttl_dns_cache=300
        )
        self._session = None

    async def __aenter__(self):
        self._session = ClientSession(connector=self._connector)
        return self

    async def __aexit__(self, *args):
        await self._session.close()
```

### Batch Operations
```python
from typing import List, Dict
import asyncio

class BatchProcessor:
    """Process items in batches."""

    async def process_batch(
        self,
        items: List[Dict],
        batch_size: int = 25
    ) -> List[Dict]:
        """Process items in batches for efficiency."""
        results = []

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = await asyncio.gather(
                *[self.process_item(item) for item in batch]
            )
            results.extend(batch_results)

        return results
```

## Monitoring and Observability

### Structured Logging
```python
from aws_lambda_powertools import Logger
from aws_lambda_powertools.logging import correlation_paths

logger = Logger(service="emoji-smith")

@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
async def handler(event: dict, context: dict) -> dict:
    """Handler with structured logging."""
    logger.info(
        "Processing request",
        extra={
            "request_id": event.get("requestContext", {}).get("requestId"),
            "user_id": event.get("requestContext", {}).get("authorizer", {}).get("claims", {}).get("sub")
        }
    )
```

### Metrics
```python
from aws_lambda_powertools import Metrics
from aws_lambda_powertools.metrics import MetricUnit

metrics = Metrics(service="emoji-smith")

@metrics.log_metrics
async def process_emoji(request: EmojiRequest) -> str:
    """Process emoji with metrics."""
    metrics.add_metric(name="EmojiRequests", unit=MetricUnit.Count, value=1)

    start_time = time.time()
    result = await generate_emoji(request)

    metrics.add_metric(
        name="EmojiGenerationTime",
        unit=MetricUnit.Seconds,
        value=time.time() - start_time
    )

    return result
```

## Quick Reference

**Before implementing infrastructure code, verify:**
- [ ] Implementing domain interfaces (protocols)
- [ ] Proper error handling and transformation
- [ ] Configuration through environment/secrets
- [ ] Appropriate logging and monitoring
- [ ] Unit tests with mocked external services
- [ ] Connection pooling for external APIs
- [ ] Retry logic for transient failures
