"""Development server for local testing."""

import uvicorn
from emojismith.app import create_app


def main() -> None:
    """Run development server."""
    app = create_app()

    uvicorn.run(  # nosec B104 - dev server binding to all interfaces is intended
        app, host="0.0.0.0", port=8000, reload=True, log_level="debug"
    )


if __name__ == "__main__":
    main()
