# ADR-002: Separate Webhook and Worker Services

## Status
Accepted

## Context
Slack requires webhook endpoints to respond within 3 seconds, but emoji generation can take 5-10 seconds. We need an architecture that:
- Responds to Slack immediately
- Handles long-running emoji generation
- Provides good user experience
- Maintains system reliability

## Decision
Use two separate services connected by a queue:

1. **Webhook service** - Handles Slack events, opens modals, enqueues jobs (< 3s)
2. **Worker service** - Processes emoji generation jobs asynchronously

Communication flow:
```
Slack → Webhook service → Queue → Worker service → Slack API
         (immediate)          (async)
```

### Current implementation (2026-01-31)

Emoji Smith currently implements this decision on GCP:

```
Slack → Cloud Run (webhook) → Pub/Sub → Cloud Run (worker) → Slack API
```

See `docs/GCP.md` for the production architecture.

## Consequences

### Positive
- Always meets Slack's 3-second deadline
- Can scale webhook and worker independently
- Failed jobs can be retried via queue retry/dead-letter configuration
- Better cost optimization (different memory/CPU needs)
- Clear separation of concerns

### Negative
- More complex deployment (2 functions)
- Additional latency from queueing
- Need to handle async job status
- Potential for lost messages

### Mitigation
- Implement correlation IDs for request tracking
- Configure alerts for queue backlog / failures
- Create runbook for debugging async flows

## Implementation Details

Implementation guidance:
- Keep the webhook service “thin” (validation + enqueue + immediate response).
- Keep AI provider API keys and slow work in the worker service.
- Ensure the queue triggers retries for transient failures and routes poison messages to a dead-letter path.

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

1. **Single service with async/background processing**
   - Rejected: Can't guarantee 3-second response time

2. **Workflow orchestration service**
   - Rejected: Overkill for this workload

3. **Direct worker invocation (no queue)**
   - Rejected: Tight coupling and weaker retry/backpressure handling

## References
- Slack Events API documentation
- `docs/GCP.md`
