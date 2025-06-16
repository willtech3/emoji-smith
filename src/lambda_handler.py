"""AWS Lambda handler for Emoji Smith."""

import json
import logging
import os
from typing import TYPE_CHECKING, Any

import boto3
from botocore.exceptions import ClientError
from mangum import Mangum

# Lazy import - only import create_app when actually needed

if TYPE_CHECKING:
    from fastapi import FastAPI

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


def get_app() -> "FastAPI":
    """Get or create the FastAPI app instance with lazy loading."""
    global _app
    if _app is None:
        import time
        
        start_total = time.time()
        logger.info("🔄 Starting app initialization...")
        
        # Profile the import
        import_start = time.time()
        from emojismith.app import create_app
        import_time = time.time() - import_start
        logger.info(f"📦 Import create_app: {import_time:.3f}s")
        
        # Profile the app creation
        creation_start = time.time()
        _app = create_app()
        creation_time = time.time() - creation_start
        logger.info(f"🏗️ create_app() execution: {creation_time:.3f}s")
        
        total_time = time.time() - start_total
        logger.info(f"✅ Total app initialization: {total_time:.3f}s")
    return _app


def handler(event: dict, context: Any) -> Any:
    """AWS Lambda handler."""
    # App initialization happens on first request for lazy loading
    app = get_app()
    mangum_handler = Mangum(app, lifespan="off")
    return mangum_handler(event, context)
