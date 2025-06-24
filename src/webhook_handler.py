"""Top-level webhook handler for Lambda.

This file exists at the package root to handle Lambda's import mechanism
while maintaining our architectural structure.
"""

from emojismith.infrastructure.aws.webhook_handler import handler

__all__ = ["handler"]
