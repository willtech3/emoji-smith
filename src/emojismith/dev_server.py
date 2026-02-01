"""Development server for local testing."""

import uvicorn

from emojismith.infrastructure.gcp.webhook_app import app


def main() -> None:
    """Run development server using the GCP webhook app."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="debug",  # nosec B104
    )


if __name__ == "__main__":
    main()
