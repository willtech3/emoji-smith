from .web.async_slack_response import AsyncSlackResponse

class SlackApiError(Exception):
    response: AsyncSlackResponse
