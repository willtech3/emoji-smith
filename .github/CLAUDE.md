# CLAUDE.md - Deployment and CI/CD Guidelines

## Inheritance
- **Extends:** /CLAUDE.md (root)
- **Overrides:** None (CRITICAL RULES cannot be overridden)
- **Scope:** All GitHub Actions workflows, CI/CD pipelines, and deployment processes

## Rules

**Context:** This document provides guidelines for working with CI/CD pipelines, CDK infrastructure, and deployment processes. Read this when configuring GitHub Actions, deploying infrastructure, or managing the deployment pipeline.

## 🚀 Deployment Philosophy

**Golden Rule:** All deployments happen through CI/CD. Manual deployments are forbidden when CI exists.

## Architecture Overview

### Dual Lambda Architecture
```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Slack     │────▶│   Webhook    │────▶│     SQS      │────▶│    Worker    │
│   Events    │     │   Lambda     │     │    Queue     │     │   Lambda     │
└─────────────┘     └──────────────┘     └──────────────┘     └──────────────┘
                           │                                            │
                           └────────────────────────────────────────────┘
                                                │
                                        ┌───────▼────────┐
                                        │  AWS Services  │
                                        │ - Secrets Mgr  │
                                        │ - CloudWatch   │
                                        │ - S3 Storage   │
                                        └────────────────┘
```

### Why Dual Lambda?
- **Webhook Lambda**: Responds within Slack's 3-second timeout
- **Worker Lambda**: Handles time-consuming image generation (10-15s)
- **Better cold starts**: Minimal dependencies in webhook
- **Scalability**: SQS provides buffering and retry logic

## CI/CD Pipeline

### GitHub Actions Workflow

Our deployment pipeline runs automatically on push to main:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main]

jobs:
  quality:
    runs-on: ubuntu-latest
    steps:
      - Code formatting (ruff format)
      - Linting + security scanning (ruff check)
      - Type checking (mypy)

  test:
    runs-on: ubuntu-latest
    steps:
      - Unit tests with coverage
      - Integration tests
      - Coverage report (>80% required)

  deploy:
    needs: [quality, test]
    runs-on: ubuntu-latest
    steps:
      - Build Docker images
      - Push to ECR
      - Deploy with CDK
```

### Environment Variables

#### Required Secrets in GitHub Actions
```
AWS_ACCOUNT_ID          # Target AWS account
AWS_REGION              # Deployment region
SLACK_BOT_TOKEN         # Bot user OAuth token
SLACK_SIGNING_SECRET    # Request verification
OPENAI_API_KEY          # Image generation API
```

#### CDK Context Variables
```json
{
  "environment": "production",
  "slackAppId": "A0XXXXXX",
  "webhookMemory": 512,
  "workerMemory": 1024,
  "enableXRay": true
}
```

## CDK Infrastructure

### Stack Organization
```
infra/
├── app.py                  # CDK app entry point
├── stacks/
│   ├── emoji_smith_stack.py    # Main stack
│   ├── lambda_stack.py         # Lambda functions
│   └── storage_stack.py        # S3, DynamoDB
└── constructs/
    ├── dual_lambda.py          # Webhook + Worker pattern
    └── sqs_processor.py        # Queue configuration
```

### Key CDK Patterns

#### Lambda Container Image
```python
from aws_cdk import aws_lambda as lambda_

webhook_function = lambda_.DockerImageFunction(
    self, "WebhookHandler",
    code=lambda_.DockerImageCode.from_image_asset(
        "../",
        file="Dockerfile.webhook",
        build_args={"FUNCTION_TYPE": "webhook"}
    ),
    memory_size=512,
    timeout=Duration.seconds(30),
    environment={
        "SQS_QUEUE_URL": queue.queue_url,
        "LOG_LEVEL": "INFO"
    }
)
```

#### SQS Dead Letter Queue
```python
dlq = sqs.Queue(
    self, "DeadLetterQueue",
    retention_period=Duration.days(14)
)

main_queue = sqs.Queue(
    self, "ProcessingQueue",
    visibility_timeout=Duration.seconds(300),
    dead_letter_queue=sqs.DeadLetterQueue(
        max_receive_count=3,
        queue=dlq
    )
)
```

#### Secrets Manager Integration
```python
secrets = secretsmanager.Secret(
    self, "EmojiSmithSecrets",
    description="API keys and tokens",
    secret_object_value={
        "slackBotToken": SecretValue.unsafe_plain_text(""),
        "openaiApiKey": SecretValue.unsafe_plain_text("")
    }
)

# Grant read access to Lambda
secrets.grant_read(lambda_function)
```

## Local Development

### Running Locally
```bash
# 1. Start local webhook server
python -m src.emojismith.dev_server

# 2. Expose to internet
ngrok http 8000

# 3. Update Slack app URL
# https://api.slack.com/apps/YOUR_APP_ID/event-subscriptions
```

### Docker Development
```bash
# Build webhook container
docker build -f Dockerfile.webhook -t emoji-webhook .

# Build worker container
docker build -f Dockerfile.worker -t emoji-worker .

# Run with environment
docker run -p 8000:8000 \
  -e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  emoji-webhook
```

## Deployment Process

### 1. Feature Branch Deployment
```bash
# Never deploy from feature branches to production
# Use development environment for testing
cd infra
cdk deploy --context environment=development
```

### 2. Production Deployment (Automatic)
```yaml
# Triggered by merge to main
# No manual steps required
# Monitor in GitHub Actions
```

### 3. Rollback Process
```bash
# Revert commit on main
git revert HEAD
git push origin main

# CI/CD will automatically deploy previous version
```

## Monitoring and Alerts

### CloudWatch Dashboards
- Lambda invocations and errors
- SQS message age and DLQ depth
- API Gateway response times
- Cost tracking by service

### Alarms Configuration
```python
# High error rate alarm
error_alarm = cloudwatch.Alarm(
    self, "HighErrorRate",
    metric=lambda_function.metric_errors(),
    threshold=10,
    evaluation_periods=2,
    datapoints_to_alarm=2
)

# SQS message age alarm
age_alarm = cloudwatch.Alarm(
    self, "OldMessages",
    metric=queue.metric_approximate_age_of_oldest_message(),
    threshold=300,  # 5 minutes
    evaluation_periods=1
)
```

### X-Ray Tracing
```python
# Enable in CDK
lambda_function = lambda_.Function(
    self, "Function",
    tracing=lambda_.Tracing.ACTIVE,
    ...
)

# Use in code
from aws_xray_sdk.core import xray_recorder

@xray_recorder.capture('process_emoji')
async def process_emoji_request(request):
    # Traced execution
    pass
```

## Security Best Practices

### IAM Least Privilege
```python
# Grant only required permissions
queue.grant_send_messages(webhook_lambda)
queue.grant_consume_messages(worker_lambda)
secrets.grant_read(worker_lambda)
bucket.grant_read_write(worker_lambda)
```

### VPC Configuration (if needed)
```python
vpc = ec2.Vpc(
    self, "EmojiSmithVPC",
    max_azs=2,
    nat_gateways=1,
    subnet_configuration=[
        ec2.SubnetConfiguration(
            name="Private",
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
        )
    ]
)

lambda_function = lambda_.Function(
    self, "Function",
    vpc=vpc,
    vpc_subnets=ec2.SubnetSelection(
        subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
    )
)
```

## Cost Optimization

### Lambda Configuration
- Right-size memory based on profiling
- Use ARM architecture for cost savings
- Enable Lambda SnapStart for Java (if applicable)

### S3 Lifecycle Policies
```python
bucket.add_lifecycle_rule(
    id="DeleteOldEmojis",
    expiration=Duration.days(90),
    transitions=[
        s3.Transition(
            storage_class=s3.StorageClass.INFREQUENT_ACCESS,
            transition_after=Duration.days(30)
        )
    ]
)
```

## Troubleshooting Deployments

### Common Issues

1. **CDK Bootstrap Required**
   ```bash
   cdk bootstrap aws://ACCOUNT-ID/REGION
   ```

2. **Docker Build Failures**
   - Check Docker daemon is running
   - Ensure sufficient disk space
   - Verify Dockerfile syntax

3. **Lambda Timeout**
   - Check CloudWatch logs
   - Verify SQS visibility timeout > Lambda timeout
   - Review memory allocation

4. **Permission Errors**
   - Check IAM roles and policies
   - Verify secrets access
   - Review resource policies

### Deployment Checklist

Before deploying:
- [ ] All tests passing
- [ ] Security scan clean
- [ ] Environment variables configured
- [ ] CDK diff reviewed
- [ ] Rollback plan ready

## Emergency Procedures

### Immediate Rollback
```bash
# If deployment causes issues
git revert HEAD --no-edit
git push origin main
```

### Disable Webhook
```python
# Emergency Lambda environment variable
MAINTENANCE_MODE=true

# In webhook handler
if os.environ.get('MAINTENANCE_MODE') == 'true':
    return {
        'statusCode': 503,
        'body': json.dumps({'message': 'Service temporarily unavailable'})
    }
```

### Manual Queue Purge
```bash
# Clear problematic messages
aws sqs purge-queue --queue-url $QUEUE_URL
```

## Quick Reference

**Deployment Commands:**
```bash
# Deploy to dev
cdk deploy --context environment=development

# Show changes
cdk diff

# Destroy stack (dev only)
cdk destroy --context environment=development
```

**Never:**
- Deploy manually to production
- Skip CI/CD pipeline
- Use `cdk deploy` without context
- Commit secrets to repository
- Ignore failed deployments