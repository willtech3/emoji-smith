FROM public.ecr.aws/lambda/python:3.12 AS builder
WORKDIR /app

# Install production dependencies
COPY requirements.lock .
RUN pip install --no-cache-dir --target /app -r requirements.lock

FROM public.ecr.aws/lambda/python:3.12-slim
# Copy dependencies from builder image
COPY --from=builder /app /var/runtime

# Copy application source
COPY src/ ${LAMBDA_TASK_ROOT}/

# Default Lambda handler
CMD ["lambda_handler.handler"]
