"""Development server for local testing."""

import uvicorn
from emojismith.app import create_app


def main() -> None:
    """Run development server."""
    app = create_app()

    uvicorn.run(
        app, host="0.0.0.0", port=8000, reload=False, log_level="debug"
    )  # nosec


if __name__ == "__main__":
    main()
