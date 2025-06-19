"""Tests for AWSSecretsLoader."""

import json
import os
from unittest.mock import Mock, patch
import pytest
from botocore.exceptions import ClientError

# Import the function directly to test it
from emojismith.infrastructure.aws.secrets_loader import AWSSecretsLoader


class TestAWSSecretsLoader:
    """Test the AWSSecretsLoader class."""

    def test_skips_when_secrets_name_not_set(self, caplog):
        """Should skip loading when SECRETS_NAME is not set."""
        loader = AWSSecretsLoader()
        with patch.dict(os.environ, {}, clear=True):
            with caplog.at_level("INFO"):
                loader.load_secrets()

        assert "SECRETS_NAME not set, skipping secrets loading" in caplog.text

    @patch("emojismith.infrastructure.aws.secrets_loader.boto3.client")
    def test_loads_secrets_successfully(self, mock_boto_client, caplog):
        """Should load secrets into environment variables."""
        # Arrange
        mock_secrets_client = Mock()
        mock_boto_client.return_value = mock_secrets_client

        secrets_response = {
            "SecretString": json.dumps(
                {
                    "SLACK_BOT_TOKEN": "xoxb-test-token",
                    "OPENAI_API_KEY": "sk-test-key",
                    "generated_password": "ignore-this",
                }
            )
        }
        mock_secrets_client.get_secret_value.return_value = secrets_response

        # Act - use clean environment to avoid existing vars
        test_env = {"SECRETS_NAME": "test-secret"}
        with patch.dict(os.environ, test_env, clear=True):
            loader = AWSSecretsLoader()
            with caplog.at_level("INFO"):
                loader.load_secrets()

            # Assert within the patched environment
            assert os.environ.get("SLACK_BOT_TOKEN") == "xoxb-test-token"
            assert os.environ.get("OPENAI_API_KEY") == "sk-test-key"
            assert "generated_password" not in os.environ

        # Assert
        mock_boto_client.assert_called_once_with("secretsmanager")
        mock_secrets_client.get_secret_value.assert_called_once_with(
            SecretId="test-secret"
        )
        assert "Successfully loaded 3 secrets from AWS" in caplog.text

    @patch("emojismith.infrastructure.aws.secrets_loader.boto3.client")
    def test_raises_client_error_on_aws_failure(self, mock_boto_client):
        """Should raise ClientError when AWS call fails."""
        # Arrange
        mock_secrets_client = Mock()
        mock_boto_client.return_value = mock_secrets_client

        error = ClientError(
            error_response={"Error": {"Code": "ResourceNotFound"}},
            operation_name="GetSecretValue",
        )
        mock_secrets_client.get_secret_value.side_effect = error

        # Act & Assert
        with patch.dict(os.environ, {"SECRETS_NAME": "test-secret"}):
            loader = AWSSecretsLoader()
            with pytest.raises(ClientError):
                loader.load_secrets()

    @patch("emojismith.infrastructure.aws.secrets_loader.boto3.client")
    def test_raises_json_decode_error_on_invalid_json(self, mock_boto_client):
        """Should raise JSONDecodeError when secret is not valid JSON."""
        # Arrange
        mock_secrets_client = Mock()
        mock_boto_client.return_value = mock_secrets_client

        secrets_response = {"SecretString": "invalid-json"}
        mock_secrets_client.get_secret_value.return_value = secrets_response

        # Act & Assert
        with patch.dict(os.environ, {"SECRETS_NAME": "test-secret"}):
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
