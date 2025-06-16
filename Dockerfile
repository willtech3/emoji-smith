# Build stage: install dependencies
FROM public.ecr.aws/lambda/python:3.12 AS builder
WORKDIR /app

# Install production dependencies only - aggressively optimized for sub-3s cold start
COPY requirements.lock .
RUN grep -v "^-e \\." requirements.lock | \
    # Keep core runtime dependencies and their essential transitive deps
    grep -E "^(aioboto3|fastapi|slack-|openai|pillow|mangum|python-dotenv|pydantic|aiohttp|boto3|certifi|httpx|jmespath|urllib3|botocore|s3transfer|multidict|yarl|aiosignal|frozenlist)" > requirements-minimal.lock && \
    pip install --no-cache-dir --target /app/python -r requirements-minimal.lock

# Copy application source (without tests/docs via .dockerignore)
COPY src/ /app/src/

# Runtime stage: minimal slim image
FROM public.ecr.aws/lambda/python:3.12-slim

# Copy python packages and application code
COPY --from=builder /app/python /var/task/
COPY --from=builder /app/src/ ${LAMBDA_TASK_ROOT}/

# Default command
CMD ["lambda_handler.handler"]
