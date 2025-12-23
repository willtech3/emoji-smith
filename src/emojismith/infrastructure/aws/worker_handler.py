"""AWS Lambda handler for SQS worker processing emoji generation jobs."""

import json
import logging
import os
from typing import Any

from emojismith.app import create_worker_emoji_service
from shared.domain.entities import EmojiGenerationJob

from .secrets_loader import AWSSecretsLoader

logger = logging.getLogger(__name__)

_secrets_loader = AWSSecretsLoader()

def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """
    AWS Lambda handler for processing SQS emoji generation jobs.

    Args:
        event: SQS event containing Records array
        context: Lambda context object

    Returns:
        Processing results with batch item failures
    """
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        _secrets_loader.load_secrets()

    emoji_service = create_worker_emoji_service()

    batch_item_failures = []

    for record in event.get("Records", []):
        try:
            message_body = json.loads(record["body"])

            job = EmojiGenerationJob.from_dict(message_body)

            logger.info(
                f"Processing emoji generation job: {job.job_id} for user {job.user_id}"
            )

            import asyncio

            asyncio.run(emoji_service.process_emoji_generation_job(job))

            logger.info(f"Successfully completed job: {job.job_id}")

        except Exception as e:
            logger.exception(f"Failed to process SQS record: {e}")

            batch_item_failures.append(
                {"itemIdentifier": record.get("messageId", "unknown")}
            )

    result = {"batchItemFailures": batch_item_failures}

    if batch_item_failures:
        logger.warning(f"Failed to process {len(batch_item_failures)} messages")
    else:
        logger.info(f"Successfully processed {len(event.get('Records', []))} messages")

    return result
