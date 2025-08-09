# Emoji Smith CDK Infrastructure

This directory contains the AWS CDK infrastructure for deploying Emoji Smith to AWS Lambda.

## Prerequisites

1. **AWS CLI configured** with appropriate credentials
2. **Node.js and npm** installed (for CDK CLI)
3. **Python 3.12** with dependencies installed

## One-time Setup

### 1. Install AWS CDK CLI
```bash
npm install -g aws-cdk
```

### 2. Configure AWS credentials
```bash
aws configure
```

### 3. Bootstrap CDK (one-time per AWS account/region)
```bash
cdk bootstrap
```

### 4. Install Python dependencies
```bash
cd infra
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

## Deployment

### 1. Activate virtual environment
```bash
cd infra
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Deploy the stack
```bash
cdk deploy
```

### 3. Configure Secrets (First deployment only)
After the first deployment, you need to add your secrets to AWS Secrets Manager:

```bash
aws secretsmanager update-secret \
  --secret-id emoji-smith/production \
  --secret-string '{
    "SLACK_BOT_TOKEN": "xoxb-your-bot-token",
    "SLACK_SIGNING_SECRET": "your-signing-secret",
    "OPENAI_API_KEY": "sk-your-openai-key",
    "OPENAI_CHAT_MODEL": "gpt-5",
    "LOG_LEVEL": "INFO"
  }'
```

## Infrastructure Components

The CDK stack creates:

- **Lambda Function**: `emoji-smith-webhook` - Handles Slack webhooks
  - Environment variables: `SECRETS_NAME`, `SQS_QUEUE_URL`, `LOG_LEVEL`
  - Runtime: Python 3.12, Memory: 512MB, Timeout: 15 minutes
- **API Gateway**: REST API with endpoints:
  - `GET /health` - Health check returning `{"status": "healthy"}`
  - `POST /webhook` - General webhook endpoint
  - `POST /slack/events` - Slack Events API
  - `POST /slack/interactive` - Slack Interactive Components
- **SQS Queues**:
  - `emoji-smith-processing` - Background job processing
  - `emoji-smith-processing-dlq` - Dead letter queue (3 retries, 14-day retention)
- **Secrets Manager**: `emoji-smith/production` - Secure secret storage
  - Required secrets: `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `OPENAI_API_KEY`
- **CloudWatch Logs**: `/aws/lambda/emoji-smith-webhook` - Application logs (30-day retention)
- **IAM Roles**: Least-privilege permissions for Lambda (SQS, Secrets Manager access)

## Testing the Deployment

### 1. Health Check
```bash
curl https://your-api-gateway-url/health
# Should return: {"status": "healthy"}
```

### 2. Configure Slack App
Update your Slack app configuration to point to:
- Event Subscriptions: `https://your-api-gateway-url/slack/events`
- Interactive Components: `https://your-api-gateway-url/slack/interactive`

## CDK Commands

- `cdk ls` - List stacks
- `cdk synth` - Synthesize CloudFormation template
- `cdk deploy` - Deploy stack
- `cdk diff` - Show differences between deployed and local
- `cdk destroy` - Delete stack (use with caution)

## Monitoring

- **CloudWatch Logs**: Monitor Lambda function logs
- **CloudWatch Metrics**: Lambda duration, errors, invocations
- **API Gateway Logs**: HTTP request/response logs

## Troubleshooting

### Lambda Function Logs
```bash
aws logs tail /aws/lambda/emoji-smith-webhook --follow
```

### Check Secrets
```bash
aws secretsmanager get-secret-value --secret-id emoji-smith/production
```

### SQS Queue Status
```bash
aws sqs get-queue-attributes --queue-url $(aws sqs get-queue-url --queue-name emoji-smith-processing --query QueueUrl --output text) --attribute-names All
```
