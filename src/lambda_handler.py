"""AWS Lambda handler for Emoji Smith."""

import json
import logging
import os

import boto3
from botocore.exceptions import ClientError
from mangum import Mangum

from emojismith.app import create_app

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


# Global variable to cache the app
_app = None


def get_app():
    """Get or create the FastAPI app instance."""
    global _app
    if _app is None:
        # Load secrets from AWS when first creating the app
        _load_secrets_from_aws()
        _app = create_app()
    return _app


def handler(event, context):
    """AWS Lambda handler."""
    # Only create app when Lambda is actually invoked
    app = get_app()
    mangum_handler = Mangum(app, lifespan="off")
    return mangum_handler(event, context)
