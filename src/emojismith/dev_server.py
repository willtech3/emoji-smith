"""Development server for local testing.

This runs the same webhook FastAPI app used in production on Cloud Run.
"""

import uvicorn
from dotenv import load_dotenv


def main() -> None:
    """Run development server."""
    load_dotenv()

    uvicorn.run(
        "emojismith.infrastructure.gcp.webhook_app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="debug",  # nosec B104
    )


if __name__ == "__main__":
    main()
