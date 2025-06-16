# Use the official AWS Lambda Python runtime
FROM public.ecr.aws/lambda/python:3.12

# Copy requirements and install dependencies
COPY requirements.lock ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.lock

# Copy source code
COPY src/ ${LAMBDA_TASK_ROOT}/
COPY src/lambda_handler.py ${LAMBDA_TASK_ROOT}/
COPY src/worker_handler.py ${LAMBDA_TASK_ROOT}/

# Set the CMD to your handler (could also be worker_handler.handler for worker Lambda)
CMD ["lambda_handler.handler"]