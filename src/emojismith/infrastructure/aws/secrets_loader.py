from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError


class AWSSecretsLoader:
    """Load secrets from AWS Secrets Manager."""

    _instance: Optional[AWSSecretsLoader] = None
    _loaded: bool = False

    def __new__(cls, secrets_name: str | None = None) -> AWSSecretsLoader:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, secrets_name: str | None = None) -> None:
        if not self._loaded:
            self._secrets_name = secrets_name or os.environ.get("SECRETS_NAME")
            self._logger = logging.getLogger(__name__)
            self.__class__._loaded = True

    def load_secrets(self) -> Dict[str, Any]:
        """Load secrets and inject them into environment variables."""
        if not self._secrets_name:
            self._logger.info("SECRETS_NAME not set, skipping secrets loading")
            return {}

        try:
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=self._secrets_name)
            secrets: Dict[str, Any] = json.loads(response["SecretString"])

            for key, value in secrets.items():
                if key != "generated_password":
                    os.environ[key] = value

            self._logger.info("Successfully loaded %d secrets from AWS", len(secrets))
            return secrets

        except ClientError as exc:
            self._logger.exception(
                "Failed to load secrets from AWS Secrets Manager: %s", exc
            )
            raise
        except json.JSONDecodeError as exc:
            self._logger.exception("Failed to parse secrets JSON: %s", exc)
            raise
        except Exception as exc:  # noqa: BLE001
            self._logger.exception("Unexpected error loading secrets: %s", exc)
            raise
