# Build stage: install dependencies
FROM public.ecr.aws/lambda/python:3.12 AS builder
WORKDIR /app

# Install production dependencies only - aggressively optimized for sub-3s cold start
# Install essential packages directly for fastest cold start
RUN pip install --no-cache-dir --target /app/python \
    aioboto3==14.3.0 \
    fastapi==0.115.12 \
    slack-bolt==1.23.0 \
    slack-sdk==3.35.0 \
    openai==1.86.0 \
    pillow==11.2.1 \
    mangum==0.19.0 \
    python-dotenv==1.1.0 \
    pydantic==2.11.7

# Copy application source (without tests/docs via .dockerignore)
COPY src/ /app/src/

# Runtime stage: AWS Lambda base image (no slim variant available)
FROM public.ecr.aws/lambda/python:3.12

# Copy python packages and application code
COPY --from=builder /app/python /var/task/
COPY --from=builder /app/src/ ${LAMBDA_TASK_ROOT}/

# Default command
CMD ["lambda_handler.handler"]
