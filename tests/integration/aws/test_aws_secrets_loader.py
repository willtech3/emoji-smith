"""Tests for AWSSecretsLoader.

Note: moto adds ~100ms overhead per test. Consider using class-level fixtures
for test suites to improve performance when testing with many AWS service mocks.
"""

import json
import os
from unittest.mock import patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

# Import the function directly to test it
from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader


@pytest.mark.integration()
class TestAWSSecretsLoader:
    """Test the AWSSecretsLoader class."""

    def setup_method(self):
        """Reset singleton before each test."""
        AWSSecretsLoader._instance = None
        AWSSecretsLoader._loaded = False

    def teardown_method(self):
        """Reset AWSSecretsLoader singleton after each test."""
        AWSSecretsLoader._instance = None
        AWSSecretsLoader._loaded = False

    def test_skips_when_secrets_name_not_set(self, caplog):
        """Should skip loading when SECRETS_NAME is not set."""
        loader = AWSSecretsLoader()
        with patch.dict(os.environ, {}, clear=True), caplog.at_level("INFO"):
            loader.load_secrets()

        assert "SECRETS_NAME not set, skipping secrets loading" in caplog.text

    def test_loads_secrets_successfully_filters_out_generated_passwords(self, caplog):
        """Should load secrets and filter out generated passwords."""
        with mock_aws():
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

            test_env = {
                "SECRETS_NAME": "test-secret",
                "AWS_DEFAULT_REGION": "us-east-1",
            }
            with patch.dict(os.environ, test_env, clear=True):
                loader = AWSSecretsLoader()
                with caplog.at_level("INFO"):
                    loader.load_secrets()

                assert os.environ.get("SLACK_BOT_TOKEN") == "xoxb-test-token"
                assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"
                assert "generated_password" not in os.environ

        assert "Successfully loaded 3 secrets from AWS" in caplog.text

    def test_raises_client_error_when_secret_does_not_exist(self):
        """Should raise ClientError when attempting to load non-existent secret."""
        with (
            mock_aws(),
            patch.dict(
                os.environ,
                {"SECRETS_NAME": "missing", "AWS_DEFAULT_REGION": "us-east-1"},
            ),
        ):
            loader = AWSSecretsLoader()
            with pytest.raises(ClientError):
                loader.load_secrets()

    def test_raises_json_decode_error_when_secret_contains_invalid_json(self):
        """Should raise JSONDecodeError when secret string cannot be parsed as JSON."""
        with mock_aws():
            client = boto3.client("secretsmanager", region_name="us-east-1")
            client.create_secret(Name="test-secret", SecretString="invalid-json")

            with patch.dict(
                os.environ,
                {"SECRETS_NAME": "test-secret", "AWS_DEFAULT_REGION": "us-east-1"},
            ):
                loader = AWSSecretsLoader()
                with pytest.raises(json.JSONDecodeError):
                    loader.load_secrets()

    @patch("emojismith.infrastructure.aws.secrets_loader.boto3.client")
    def test_raises_exception_on_unexpected_error(self, mock_boto_client):
        """Should raise Exception on unexpected errors."""
        mock_boto_client.side_effect = Exception("Unexpected error")

        with patch.dict(os.environ, {"SECRETS_NAME": "test-secret"}):
            loader = AWSSecretsLoader()
            with pytest.raises(Exception, match="Unexpected error"):
                loader.load_secrets()
