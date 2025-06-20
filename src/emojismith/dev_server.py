"""Development server for local testing."""

import uvicorn
from emojismith.application.create_webhook_app import create_webhook_app
from emojismith.presentation.web.slack_webhook_api import create_webhook_api


def main() -> None:
    """Run development server."""
    handler = create_webhook_app()
    app = create_webhook_api(handler)

    uvicorn.run(
        app, host="0.0.0.0", port=8000, reload=False, log_level="debug"  # nosec B104
    )


if __name__ == "__main__":
    main()
