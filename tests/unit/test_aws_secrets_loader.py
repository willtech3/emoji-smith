"""Tests for AWSSecretsLoader."""

import json
import os
from unittest.mock import patch
import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

# Import the function directly to test it
from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader


class TestAWSSecretsLoader:
    """Test the AWSSecretsLoader class."""

    def setup_method(self):
        """Reset singleton before each test."""
        AWSSecretsLoader._instance = None
        AWSSecretsLoader._loaded = False

    def test_skips_when_secrets_name_not_set(self, caplog):
        """Should skip loading when SECRETS_NAME is not set."""
        with patch.dict(
            os.environ,
            {
                "AWS_DEFAULT_REGION": "us-east-1",
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
            },
            clear=True,
        ):
            loader = AWSSecretsLoader()
            with caplog.at_level("INFO"):
                loader.load_secrets()

        assert "SECRETS_NAME not set, skipping secrets loading" in caplog.text

    @mock_aws
    def test_loads_secrets_successfully(self, caplog):
        """Should load secrets into environment variables."""
        with patch.dict(
            os.environ,
            {
                "SECRETS_NAME": "test-secret",
                "AWS_DEFAULT_REGION": "us-east-1",
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
            },
            clear=True,
        ):
            client = boto3.client("secretsmanager", region_name="us-east-1")
            client.create_secret(
                Name="test-secret",
                SecretString=json.dumps(
                    {
                        "SLACK_BOT_TOKEN": "xoxb-test-token",
                        "OPENAI_API_KEY": "sk-test-key",
                        "generated_password": "ignore-this",
                    }
                ),
            )

            loader = AWSSecretsLoader()
            with caplog.at_level("INFO"):
                loader.load_secrets()

            assert os.environ.get("SLACK_BOT_TOKEN") == "xoxb-test-token"
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"
            assert "generated_password" not in os.environ

        assert "Successfully loaded 3 secrets from AWS" in caplog.text

    @mock_aws
    def test_raises_client_error_on_aws_failure(self):
        """Should raise ClientError when secret does not exist."""
        with patch.dict(
            os.environ,
            {
                "SECRETS_NAME": "missing",
                "AWS_DEFAULT_REGION": "us-east-1",
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
            },
        ):
            loader = AWSSecretsLoader()
            with pytest.raises(ClientError):
                loader.load_secrets()

    @mock_aws
    def test_raises_json_decode_error_on_invalid_json(self):
        """Should raise JSONDecodeError when secret is not valid JSON."""
        with patch.dict(
            os.environ,
            {
                "SECRETS_NAME": "test-secret",
                "AWS_DEFAULT_REGION": "us-east-1",
                "AWS_ACCESS_KEY_ID": "test",
                "AWS_SECRET_ACCESS_KEY": "test",
            },
        ):
            client = boto3.client("secretsmanager", region_name="us-east-1")
            client.create_secret(Name="test-secret", SecretString="invalid-json")

            loader = AWSSecretsLoader()
            with pytest.raises(json.JSONDecodeError):
                loader.load_secrets()

    @patch("emojismith.infrastructure.aws.secrets_loader.boto3.client")
    def test_raises_exception_on_unexpected_error(self, mock_boto_client):
        """Should raise Exception on unexpected errors."""
        # Arrange
        mock_boto_client.side_effect = Exception("Unexpected error")

        # Act & Assert
        with patch.dict(os.environ, {"SECRETS_NAME": "test-secret"}):
            loader = AWSSecretsLoader()
            with pytest.raises(Exception, match="Unexpected error"):
                loader.load_secrets()
