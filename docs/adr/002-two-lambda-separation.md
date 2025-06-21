# ADR-002: Separate Webhook and Worker Lambdas

## Status
Accepted

## Context
Slack requires webhook endpoints to respond within 3 seconds, but emoji generation can take 5-10 seconds. We need an architecture that:
- Responds to Slack immediately
- Handles long-running emoji generation
- Provides good user experience
- Maintains system reliability

## Decision
Use two separate Lambda functions connected by SQS:

1. **Webhook Lambda** - Handles Slack events, opens modals, queues jobs (< 3s)
2. **Worker Lambda** - Processes emoji generation jobs asynchronously (up to 30s)

Communication flow:
```
Slack → Webhook Lambda → SQS Queue → Worker Lambda → Slack API
         (immediate)                    (async)
```

## Consequences

### Positive
- Always meets Slack's 3-second deadline
- Can scale webhook and worker independently
- Failed jobs can be retried via SQS DLQ
- Better cost optimization (different memory/CPU needs)
- Clear separation of concerns

### Negative
- More complex deployment (2 functions)
- Additional latency from queueing
- Need to handle async job status
- Potential for lost messages

### Mitigation
- Use SQS FIFO for ordering guarantees
- Implement correlation IDs for request tracking
- Add CloudWatch alarms for queue depth
- Create runbook for debugging async flows

## Implementation Details

### Webhook Lambda Configuration
```python
# CDK configuration
webhook_function = lambda_.Function(
    self, "WebhookFunction",
    memory_size=512,  # Fast response, low memory
    timeout=Duration.seconds(10),
    environment={
        "SQS_QUEUE_URL": queue.queue_url
    }
)
```

### Worker Lambda Configuration
```python
# CDK configuration
worker_function = lambda_.Function(
    self, "WorkerFunction",
    memory_size=1024,  # Image generation needs more memory
    timeout=Duration.seconds(30),
    environment={
        "OPENAI_API_KEY": secret.secret_arn
    }
)

# SQS trigger
worker_function.add_event_source(
    SqsEventSource(queue, batch_size=1)
)
```

### Job Message Format
```json
{
    "job_id": "job_123",
    "correlation_id": "req_456",
    "user_id": "U123456",
    "channel_id": "C789012",
    "emoji_spec": {
        "description": "happy dance",
        "style": "cartoon"
    },
    "timestamp": "2024-01-15T10:30:00Z"
}
```

## Alternatives Considered

1. **Single Lambda with async processing**
   - Rejected: Can't guarantee 3-second response time

2. **Step Functions**
   - Rejected: Overkill for simple async job

3. **Direct Lambda invocation**
   - Rejected: No retry mechanism, tight coupling

## References
- Slack Events API documentation
- AWS Lambda best practices
- SQS FIFO queues documentation
