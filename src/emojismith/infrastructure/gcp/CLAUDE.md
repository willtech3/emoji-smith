# GCP Infrastructure Guidelines

## 🏗️ Architecture

- **Pub/Sub Job Queue**: Uses `PubSubJobQueue` adapter (async wrapper around sync `google-cloud-pubsub`)
- **Webhook App**: Cloud Run service running FastAPI directly (no platform-specific handler wrapper)
- **Worker App**: Cloud Run service processing Pub/Sub push messages (FastAPI)

## 🔒 Security

- Secrets are injected as environment variables by Cloud Run (from Secret Manager)
- Do NOT commit secrets or API keys
- Worker endpoint should be protected (only invokable by Pub/Sub service account)

## 🧪 Testing

- Mock `google.cloud.pubsub_v1.PublisherClient` for unit tests
- Use integration tests to verify Pub/Sub publishing
