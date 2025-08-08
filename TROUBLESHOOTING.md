# Emoji Smith Troubleshooting Guide

## Common Issues and Solutions

### 🔴 Mypy Type Errors

**Symptoms:**
```
error: Cannot find implementation or library stub for module named "mangum"
error: Skipping analyzing "boto3": module is installed, but missing library stubs
```

**Solution:**
```bash
# 1. Ensure virtual environment is activated
source .venv/bin/activate

# 2. Sync all dependencies including type stubs
uv sync --all-extras

# 3. Verify Python version
python --version  # Should be 3.12.x

# 4. Run mypy again
mypy src/
```

---

### 🔴 Import Errors in Tests

**Symptoms:**
```
ImportError: cannot import name 'EmojiService' from 'emojismith.application'
```

**Solution:**
1. Check if module is in correct location per architecture:
   - Domain: `src/domain/`
   - Application: `src/application/`
   - Infrastructure: `src/infrastructure/`

2. Ensure `__init__.py` files exist in all directories

3. Run tests with proper Python path:
   ```bash
   pytest tests/  # Not python -m pytest
   ```

---

### 🔴 Pre-commit Hook Failures

**Symptoms:**
Pre-commit fails even though individual tools pass

**Solution:**
```bash
# Update pre-commit hooks
pre-commit autoupdate

# Run on all files to reset state
pre-commit run --all-files

# If still failing, check specific hook
pre-commit run mypy --all-files -v
```

---

### 🔴 Lambda Deployment Failures

**Symptoms:**
- CDK deploy fails with "Handler not found"
- Lambda function fails to start

**Common Causes:**

1. **Handler path incorrect**
   ```python
   # Handler MUST be at these exact paths:
   src/emojismith/infrastructure/aws/webhook_handler.py
   src/emojismith/infrastructure/aws/worker_handler.py
   ```

2. **Missing dependencies in webhook package**
   ```bash
   # Check webhook-specific requirements
   cat requirements-webhook.txt

   # Rebuild webhook package
   ./scripts/build_webhook_package.sh
   ```

3. **Import errors in Lambda**
   - Check CloudWatch logs for specific import error
   - Ensure all required packages are in requirements-webhook.txt

---

### 🔴 Slack Modal Not Opening

**Symptoms:**
- Click "Create Emoji" but nothing happens
- No errors in logs

**Debug Steps:**

1. **Check webhook signature validation**
   ```python
   # Add debug logging in webhook handler
   logger.info(f"Signature valid: {is_valid}")
   ```

2. **Verify trigger_id is fresh** (expires in 3 seconds)
   ```python
   logger.info(f"Trigger ID age: {time.time() - float(timestamp)}")
   ```

3. **Check Slack API response**
   ```python
   response = await slack_client.views_open(...)
   logger.info(f"Slack response: {response}")
   ```

---

### 🔴 Emoji Generation Timeout

**Symptoms:**
- Modal shows "Failed to queue emoji generation"
- Lambda timeout errors

**Solutions:**

1. **Increase Lambda timeout**
   ```python
   # infra/app_stack.py
   timeout=Duration.seconds(30)  # Increase from 10
   ```

2. **Check OpenAI API response time**
   ```python
   start = time.time()
   response = await openai_client.images.generate(...)
   logger.info(f"gpt-image-1 took {time.time() - start}s")
   ```

3. **Optimize prompt generation**
   - Reduce prompt complexity
   - Use DALL-E 2 for faster generation

---

### 🔴 SQS Message Processing Failures

**Symptoms:**
- Messages in DLQ (Dead Letter Queue)
- Worker Lambda errors

**Debug Process:**

1. **Check DLQ messages**
   ```bash
   aws sqs receive-message --queue-url $DLQ_URL
   ```

2. **Common issues:**
   - Message format mismatch
   - Missing required fields
   - JSON parsing errors

3. **Fix and replay**
   ```python
   # Replay DLQ messages after fix
   ./scripts/replay_dlq_messages.py
   ```

---

### 🔴 Dual Lambda Architecture Issues

**Issue: Webhook Lambda times out waiting for Worker Lambda**

**Symptoms:**
- Slack shows timeout error after 3 seconds
- CloudWatch shows webhook completed but no worker execution

**Solution:**
1. Verify SQS queue configuration:
   ```bash
   aws sqs get-queue-attributes --queue-url $SQS_QUEUE_URL \
     --attribute-names VisibilityTimeout,MessageRetentionPeriod
   ```

2. Check Lambda permissions for SQS:
   ```bash
   aws lambda get-policy --function-name emoji-smith-worker | jq
   ```

3. Monitor queue depth:
   ```bash
   aws sqs get-queue-attributes --queue-url $SQS_QUEUE_URL \
     --attribute-names ApproximateNumberOfMessages
   ```

**Issue: Messages stuck in SQS queue**

**Symptoms:**
- Queue depth increasing
- Worker Lambda not processing messages

**Debug Steps:**
1. Check Worker Lambda triggers:
   ```bash
   aws lambda list-event-source-mappings \
     --function-name emoji-smith-worker
   ```

2. Verify message format matches expectations
3. Check Worker Lambda CloudWatch logs for errors

**Issue: Inconsistent behavior between local and production**

**Local Development Tips:**
- Without SQS: Jobs process synchronously (good for debugging)
- With local SQS: Use LocalStack or ElasticMQ
  ```bash
  # LocalStack example
  docker run -d -p 4566:4566 localstack/localstack
  export SQS_QUEUE_URL=http://localhost:4566/000000000000/emoji-queue
  ```

---

## Performance Issues

### 🟡 Slow Cold Starts

**Symptoms:**
- First request takes 5-10 seconds
- Subsequent requests are fast

**Optimizations:**

1. **Reduce package size**
   ```bash
   # Check package sizes
   pip list --format=freeze | xargs pip show | grep -E "^(Name|Location|Size)"

   # Remove unnecessary dependencies
   uv pip uninstall unused-package
   ```

2. **Lazy imports**
   ```python
   # Instead of top-level imports
   def handle_request():
       from heavy_library import HeavyClass  # Import when needed
   ```

3. **Use Lambda SnapStart** (for Java runtimes) or consider Lambda@Edge

---

### 🟡 High Memory Usage

**Symptoms:**
- Lambda function running out of memory
- Slow image processing

**Solutions:**

1. **Monitor memory usage**
   ```python
   import tracemalloc
   tracemalloc.start()

   # Your code here

   current, peak = tracemalloc.get_traced_memory()
   logger.info(f"Current memory: {current / 10**6:.1f} MB")
   ```

2. **Stream large files**
   ```python
   # Don't load entire image into memory
   async for chunk in response.aiter_bytes():
       process_chunk(chunk)
   ```

---

## Debugging Techniques

### CloudWatch Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/emoji-smith-webhook --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/emoji-smith-worker \
  --filter-pattern "ERROR"

# Get logs for specific request
aws logs filter-log-events \
  --log-group-name /aws/lambda/emoji-smith-webhook \
  --filter-pattern "{$.correlation_id = \"abc-123\"}"

# Query across webhook and worker logs
aws logs insights query \
  --log-group-names /aws/lambda/emoji-smith-webhook /aws/lambda/emoji-smith-worker \
  --start-time $(date -u -d '1 hour ago' +%s) \
  --end-time $(date +%s) \
  --query 'fields @timestamp, @message | filter correlation_id = "abc-123" | sort @timestamp'

# Find slow emoji generations
aws logs insights query \
  --log-group-names /aws/lambda/emoji-smith-worker \
  --query 'fields @timestamp, duration | filter duration > 5000 | stats avg(duration), max(duration), count()'

# Monitor SQS dead letter queue
aws cloudwatch get-metric-statistics \
  --namespace AWS/SQS \
  --metric-name ApproximateNumberOfMessagesVisible \
  --dimensions Name=QueueName,Value=emoji-smith-dlq \
  --statistics Average \
  --start-time $(date -u -d '1 hour ago' --iso-8601) \
  --end-time $(date -u --iso-8601) \
  --period 300
```

### Local Lambda Testing

```python
# Test Lambda handler locally
from emojismith.infrastructure.aws.webhook_handler import handler

event = {
    "body": '{"type": "url_verification", "challenge": "test"}',
    "headers": {"X-Slack-Signature": "..."}
}

response = handler(event, {})
print(response)
```

### Correlation IDs

Track requests across services:

```python
# Generate in webhook
correlation_id = str(uuid.uuid4())
logger = logger.bind(correlation_id=correlation_id)

# Pass to worker via SQS
message["correlation_id"] = correlation_id

# Use in worker
logger = logger.bind(correlation_id=message["correlation_id"])
```

---

## Getting Help

1. **Search existing issues**
   ```bash
   gh issue list --search "your error message"
   ```

2. **Check ADRs for design decisions**
   ```bash
   ls docs/adr/
   ```

3. **Ask for help with context**
   ```bash
   # Generate debug bundle
   ./scripts/debug_bundle.sh

   # Creates debug_bundle.zip with:
   # - Environment info
   # - Recent logs
   # - Configuration (sanitized)
   ```

4. **Open an issue**
   ```bash
   gh issue create --title "Brief description" \
     --body "## Environment\n\n## Steps to Reproduce\n\n## Expected\n\n## Actual"
   ```

---

## Prevention Tips

1. **Always work in activated venv**
   ```bash
   # Add to your shell profile
   alias emoji="cd ~/emoji-smith && source .venv/bin/activate"
   ```

2. **Run checks before pushing**
   ```bash
   # Create git pre-push hook
   echo './scripts/check-quality.sh' > .git/hooks/pre-push
   chmod +x .git/hooks/pre-push
   ```

3. **Keep dependencies updated**
   ```bash
   # Weekly dependency update
   uv pip compile requirements.in -o requirements.txt --upgrade
   ```

4. **Monitor Lambda metrics**
   - Set up CloudWatch alarms for errors
   - Track cold start frequency
   - Monitor memory usage trends
