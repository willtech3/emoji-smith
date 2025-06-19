import json
import logging
import os
from typing import Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class AWSSecretsLoader:
    """Load secrets from AWS Secrets Manager into environment variables."""

    def __init__(self, client: Optional[boto3.client] = None) -> None:
        self._client = client

    def load(self, secrets_name: Optional[str]) -> None:
        """Load secrets by name if provided."""
        if not secrets_name:
            logger.info("SECRETS_NAME not set, skipping secrets loading")
            return

        try:
            client = self._client or boto3.client("secretsmanager")
            self._client = client
            response = client.get_secret_value(SecretId=secrets_name)
            secrets = json.loads(response["SecretString"])

            for key, value in secrets.items():
                if key != "generated_password":
                    os.environ[key] = value

            logger.info("Successfully loaded %d secrets from AWS", len(secrets))

        except ClientError as e:
            logger.exception("Failed to load secrets from AWS Secrets Manager: %s", e)
            raise
        except json.JSONDecodeError as e:
            logger.exception("Failed to parse secrets JSON: %s", e)
            raise
        except Exception as e:
            logger.exception("Unexpected error loading secrets: %s", e)
            raise
