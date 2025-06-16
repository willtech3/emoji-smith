# Multi-stage build to reduce final image size

# Build stage - install dependencies
FROM public.ecr.aws/lambda/python:3.12 AS builder
WORKDIR /app
COPY requirements.lock .
RUN pip install --no-cache-dir --target /app -r requirements.lock

# Runtime stage - minimal image
FROM public.ecr.aws/lambda/python:3.12-slim
COPY --from=builder /app /var/runtime
COPY src/ ${LAMBDA_TASK_ROOT}/

CMD ["lambda_handler.handler"]
