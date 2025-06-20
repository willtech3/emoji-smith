# Optimized single-stage build for fastest Lambda cold start
FROM public.ecr.aws/lambda/python:3.12

# Install essential dependencies directly for sub-3s cold start
RUN pip install --no-cache-dir \
    aioboto3==14.3.0 \
    fastapi==0.115.12 \
    slack-bolt==1.23.0 \
    slack-sdk==3.35.0 \
    openai==1.86.0 \
    pillow==11.2.1 \
    mangum==0.19.0 \
    python-dotenv==1.1.0 \
    pydantic==2.11.7 && \
    # Optimize container size
    rm -rf /root/.cache/pip/* && \
    find /var/lang -name "*.pyc" -delete && \
    find /var/lang -name "__pycache__" -exec rm -rf {} + || true

# Copy application source directly to Lambda task root
COPY src/ ${LAMBDA_TASK_ROOT}/

# Default command
CMD ["emojismith.infrastructure.aws.worker_handler.handler"]
