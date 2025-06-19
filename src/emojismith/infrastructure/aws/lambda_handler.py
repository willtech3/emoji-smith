"""AWS Lambda handler for Emoji Smith."""

import logging
import os
from typing import TYPE_CHECKING, Any

from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader
from mangum import Mangum

# Lazy import - only import create_app when actually needed

if TYPE_CHECKING:
    from fastapi import FastAPI

# Configure logging
logger = logging.getLogger(__name__)

_secrets_loader = AWSSecretsLoader()


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
    return _app  # type: ignore[no-any-return]


def handler(event: dict, context: Any) -> Any:
    """AWS Lambda handler."""
    import time

    handler_start = time.time()
    logger.info("🚀 Lambda handler started")

    # Load secrets first if in AWS environment
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        secrets_start = time.time()
        logger.info("🔐 Loading secrets from AWS...")
        _secrets_loader.load(os.environ.get("SECRETS_NAME"))
        secrets_time = time.time() - secrets_start
        logger.info(f"✅ Secrets loaded: {secrets_time:.3f}s")

    # App initialization happens on first request for lazy loading
    app_start = time.time()
    app = get_app()
    app_time = time.time() - app_start
    logger.info(f"📱 App ready: {app_time:.3f}s")

    mangum_start = time.time()
    mangum_handler = Mangum(app, lifespan="off")
    mangum_time = time.time() - mangum_start
    logger.info(f"🔗 Mangum handler: {mangum_time:.3f}s")

    total_time = time.time() - handler_start
    logger.info(f"🏁 Total handler time: {total_time:.3f}s")

    return mangum_handler(event, context)
