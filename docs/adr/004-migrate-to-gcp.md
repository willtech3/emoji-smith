# ADR-004: Migrate Deployment from AWS to GCP

## Status
Accepted

## Context
Emoji Smith was originally deployed on AWS using a dual Lambda architecture and an SQS queue (see ADR-002). As of **2026-01-31**, production runs on Google Cloud Platform.

Key goals of the migration:
- Keep the “fast webhook + async worker” runtime separation required by Slack timeouts
- Reduce operational complexity by using a container-native runtime
- Use keyless CI/CD authentication and keep secrets out of the repo

## Decision
Deploy Emoji Smith on GCP using:
- **Cloud Run** for the webhook service (public)
- **Pub/Sub** for the async job queue (push subscription)
- **Cloud Run** for the worker service (private)
- **Secret Manager** for runtime secrets (injected as env vars)
- **Artifact Registry** for container images

Current architecture:
```
Slack → Cloud Run (webhook) → Pub/Sub → Cloud Run (worker) → Slack API
```

## Consequences

### Positive
- Single runtime model (containers) for both services
- Clear separation between request/ack and long-running work
- Keyless CI/CD via Workload Identity Federation
- Secrets managed via GCP Secret Manager and injected at runtime

### Negative
- Required rewriting infrastructure-as-code and deployment process
- New operational surface area (Cloud Run + Pub/Sub configuration)

## References
- `README.md` (current deployment + architecture)
- ADR-002 (historical: original “webhook + worker” separation)

