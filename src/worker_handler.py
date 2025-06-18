"""AWS Lambda handler for SQS worker processing emoji generation jobs."""

import json
import logging
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

from shared.domain.entities import EmojiGenerationJob

# Configure logging
logger = logging.getLogger(__name__)


def _load_secrets_from_aws() -> None:
    """Load secrets from AWS Secrets Manager into environment variables."""
    secrets_name = os.environ.get("SECRETS_NAME")
    if not secrets_name:
        logger.info("SECRETS_NAME not set, skipping secrets loading")
        return

    try:
        secrets_client = boto3.client("secretsmanager")
        response = secrets_client.get_secret_value(SecretId=secrets_name)
        secrets = json.loads(response["SecretString"])

        # Set environment variables from secrets
        for key, value in secrets.items():
            if key != "generated_password":  # Skip auto-generated password
                os.environ[key] = value

        logger.info(f"Successfully loaded {len(secrets)} secrets from AWS")

    except ClientError as e:
        logger.exception(f"Failed to load secrets from AWS Secrets Manager: {e}")
        raise
    except json.JSONDecodeError as e:
        logger.exception(f"Failed to parse secrets JSON: {e}")
        raise
    except Exception as e:
        logger.exception(f"Unexpected error loading secrets: {e}")
        raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler for processing SQS emoji generation jobs.

    Args:
        event: SQS event containing Records array
        context: Lambda context object

    Returns:
        Processing results with batch item failures
    """
    # Secrets are now injected as environment variables at deploy time
    # No need to load from Secrets Manager at runtime

    # Initialize the emoji service
    from emojismith.application.services.emoji_service import EmojiCreationService
    from emojismith.infrastructure.slack.slack_api import SlackAPIRepository
    from emojismith.infrastructure.openai.openai_api import OpenAIAPIRepository
    from emojismith.infrastructure.image.processing import PillowImageProcessor
    from emojismith.infrastructure.image.pil_image_validator import PILImageValidator
    from emojismith.domain.services.generation_service import EmojiGenerationService
    from emojismith.domain.services.emoji_validation_service import (
        EmojiValidationService,
    )
    from emojismith.infrastructure.slack.slack_file_sharing import (
        SlackFileSharingRepository,
    )
    from slack_sdk.web.async_client import AsyncWebClient
    from openai import AsyncOpenAI

    # Recreate dependencies (since Lambda is stateless)
    slack_token = os.getenv("SLACK_BOT_TOKEN")
    slack_client = AsyncWebClient(token=slack_token)
    slack_repo = SlackAPIRepository(slack_client)

    openai_api_key = os.getenv("OPENAI_API_KEY")
    openai_client = AsyncOpenAI(api_key=openai_api_key)
    chat_model = os.getenv("OPENAI_CHAT_MODEL", "o3")
    openai_repo = OpenAIAPIRepository(openai_client, model=chat_model)
    image_processor = PillowImageProcessor()

    image_validator = PILImageValidator()
    emoji_validation_service = EmojiValidationService(image_validator)

    generator = EmojiGenerationService(
        openai_repo=openai_repo,
        image_processor=image_processor,
        emoji_validator=emoji_validation_service,
    )

    file_sharing_repo = SlackFileSharingRepository(slack_client)

    emoji_service = EmojiCreationService(
        slack_repo=slack_repo,
        emoji_generator=generator,
        job_queue=None,  # Worker doesn't need to queue jobs
        file_sharing_repo=file_sharing_repo,
    )

    # Process SQS records
    batch_item_failures = []

    for record in event.get("Records", []):
        try:
            # Parse the SQS message body
            message_body = json.loads(record["body"])

            # Parse emoji generation job directly
            job = EmojiGenerationJob.from_dict(message_body)

            logger.info(
                f"Processing emoji generation job: {job.job_id} for user {job.user_id}"
            )

            # Process the job using async handler
            import asyncio

            asyncio.run(emoji_service.process_emoji_generation_job(job))

            logger.info(f"Successfully completed job: {job.job_id}")

        except Exception as e:
            logger.exception(f"Failed to process SQS record: {e}")

            # Add to batch item failures for SQS retry
            batch_item_failures.append(
                {"itemIdentifier": record.get("messageId", "unknown")}
            )

    # Return batch item failures for SQS to retry
    result = {"batchItemFailures": batch_item_failures}

    if batch_item_failures:
        logger.warning(f"Failed to process {len(batch_item_failures)} messages")
    else:
        logger.info(f"Successfully processed {len(event.get('Records', []))} messages")

    return result
