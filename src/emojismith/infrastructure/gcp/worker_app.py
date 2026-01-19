"""Cloud Run worker application for processing Pub/Sub push messages."""

import base64
import json
import logging
import time

from fastapi import FastAPI, HTTPException, Request

from emojismith.app import create_worker_emoji_service
from shared.domain.dtos import EmojiGenerationJobDto
from shared.infrastructure.logging import log_event, setup_logging, trace_id_var

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI()


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/pubsub")
async def process_pubsub_message(request: Request) -> dict:
    """
    Handle Pub/Sub push messages.
    """
    try:
        envelope = await request.json()

        if not envelope or "message" not in envelope:
            raise HTTPException(
                status_code=400, detail="Invalid Pub/Sub message format"
            )

        message = envelope["message"]
        message_id = message.get("messageId", "unknown")

        # Decode the job data
        if "data" not in message:
            raise HTTPException(status_code=400, detail="Missing message data")

        job_data = base64.b64decode(message["data"]).decode("utf-8")
        job_dict = json.loads(job_data)

        job = EmojiGenerationJobDto(**job_dict)

        # Set trace context from incoming job
        trace_id_var.set(job.trace_id or job.job_id)

        log_event(
            logger,
            logging.INFO,
            "Processing job from Pub/Sub",
            event="job_received",
            job_id=job.job_id,
            user_id=job.user_id,
            image_provider=job.image_provider,
            message_id=message_id,
        )

        emoji_service = create_worker_emoji_service()

        start_time = time.monotonic()
        await emoji_service.process_emoji_generation_job(job)
        duration_ms = int((time.monotonic() - start_time) * 1000)

        log_event(
            logger,
            logging.INFO,
            "Job completed",
            event="job_completed",
            job_id=job.job_id,
            duration_ms=duration_ms,
        )

        return {"status": "ok", "messageId": message_id}

    except Exception as e:
        logger.exception(f"Error processing Pub/Sub message: {e}")
        # Return 500 to trigger Pub/Sub retry
        raise HTTPException(status_code=500, detail=str(e)) from e
