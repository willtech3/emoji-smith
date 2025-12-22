# Dual Lambda Architecture Guide

## Overview

Emoji Smith uses a dual Lambda architecture to optimize performance and cost:

- **Webhook Lambda**: Fast, minimal package deployment for immediate Slack responses
- **Worker Lambda**: Full container deployment with AI capabilities for emoji generation

## Architecture Benefits

- **Performance**: Webhook response time reduced from 5.7s → <1s
- **Reliability**: Eliminates trigger_id expiration (3-second limit) errors
- **Cost**: Lower memory usage for webhook processing (512MB vs 1024MB)

## Local Development

### Running Both Lambdas Locally

1. **Webhook Lambda** (FastAPI development server):
```bash
# Terminal 1: Start webhook server
source .venv/bin/activate
uvicorn emojismith.infrastructure.aws.webhook_handler:app --reload --port 8000

# Update Slack app webhook URL to ngrok tunnel
ngrok http 8000
```

2. **Worker Lambda** (simulate SQS processing):
```bash
# Terminal 2: Run worker for job processing
source .venv/bin/activate
python -m src.emojismith.dev_server --worker-mode
```

### Environment Variables

Both lambdas require:
```bash
# .env file
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_SIGNING_SECRET=your-secret
OPENAI_API_KEY=sk-your-key
GOOGLE_API_KEY=your-google-key     # Optional: enables Gemini provider
SQS_QUEUE_URL=https://sqs.region.amazonaws.com/account/queue-name
```

## Multi-Provider Image Generation

The worker Lambda supports multiple image generation providers:

### Provider Selection Flow
```
Slack Modal → User selects provider → Job queued with provider field
    ↓
Worker Lambda → ImageGeneratorFactory.create(provider)
    ↓
Provider-specific repository (OpenAI or Gemini) generates image
```

### Supported Providers

| Provider | Models | Fallback |
|----------|--------|----------|
| OpenAI | gpt-image-1 | gpt-image-1-mini |
| Google Gemini | gemini-3-pro-image-preview | gemini-2.5-flash-image |

### Architecture Benefits
- **Factory Pattern**: `ImageGeneratorFactory` creates provider instances on-demand
- **Per-Job Selection**: Each job specifies its provider (stored in `image_provider` field)
- **Backward Compatibility**: Jobs without `image_provider` default to OpenAI

## Deployment

### Build Webhook Package
```bash
# Generate webhook package for Lambda deployment
./scripts/build_webhook_package.sh
```
The script bundles the webhook code along with the shared domain modules so the
runtime has everything it needs.

### CDK Deployment
```bash
cd infra
cdk deploy
```

This creates:
- Package Lambda for webhook processing
- Container Lambda for worker processing
- SQS queue for communication
- API Gateway for webhook endpoints

## Testing

### Unit Tests
```bash
# Test webhook package
pytest tests/unit/webhook/

# Test worker package
pytest tests/unit/application/ tests/unit/domain/
```

### Integration Tests
```bash
# Test end-to-end flow
pytest tests/integration/test_dual_lambda_e2e.py
```

### Manual Testing
1. Send Slack message action → webhook opens modal immediately
2. Submit modal → job queued to SQS
3. Worker processes job → emoji uploaded to Slack

## Monitoring

- **CloudWatch Logs**: `/aws/lambda/webhook-function` and `/aws/lambda/worker-function`
- **Metrics**: Response times, error rates, SQS queue depth
- **Alarms**: Configure for failed webhook responses or worker timeouts

## Troubleshooting

### Common Issues

1. **Webhook timeout**: Check if modal opening is blocking
2. **Worker timeout**: Verify OpenAI API connectivity
3. **SQS delivery**: Ensure queue permissions and URL configuration
4. **Slack signature validation**: Verify signing secret matches

### Debug Commands
```bash
# Check webhook package contents
unzip -l webhook_package.zip

# Test SQS connectivity
aws sqs get-queue-attributes --queue-url $SQS_QUEUE_URL

# Validate Slack webhook
curl -X POST localhost:8000/slack/events -d @test_payload.json
```
