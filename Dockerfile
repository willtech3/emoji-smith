# Build stage: install dependencies
FROM public.ecr.aws/lambda/python:3.12 AS builder
WORKDIR /app

# Install production dependencies only
COPY requirements.lock .
RUN grep -v "^-e \\." requirements.lock > requirements-no-editable.lock \
    && pip install --no-cache-dir --target /app/python -r requirements-no-editable.lock

# Copy application source (without tests/docs via .dockerignore)
COPY src/ /app/src/

# Runtime stage: minimal slim image
FROM public.ecr.aws/lambda/python:3.12-slim

# Copy python packages and application code
COPY --from=builder /app/python /var/task/
COPY --from=builder /app/src/ ${LAMBDA_TASK_ROOT}/

# Default command
CMD ["lambda_handler.handler"]
