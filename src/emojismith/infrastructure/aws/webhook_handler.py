"""AWS Lambda adapter for the Slack webhook FastAPI app."""

from mangum import Mangum

from emojismith.application.create_webhook_app import create_webhook_app

app = create_webhook_app()
handler = Mangum(app)
