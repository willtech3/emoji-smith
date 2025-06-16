# Use the official AWS Lambda Python runtime
FROM public.ecr.aws/lambda/python:3.12

# Copy source code first for editable install
COPY src/ ${LAMBDA_TASK_ROOT}/
COPY src/lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY src/worker_handler.py ${LAMBDA_TASK_ROOT}/
COPY pyproject.toml ${LAMBDA_TASK_ROOT}/

# Copy requirements and install dependencies (excluding editable install)
COPY requirements.lock ${LAMBDA_TASK_ROOT}/
RUN grep -v "^-e \." requirements.lock > requirements-no-editable.lock && \
    pip install --no-cache-dir -r requirements-no-editable.lock

# Set the CMD to your handler (could also be worker_handler.handler for worker Lambda)
CMD ["lambda_handler.handler"]
