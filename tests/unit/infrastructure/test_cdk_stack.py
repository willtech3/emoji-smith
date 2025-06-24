"""Test CDK stack configuration to prevent Lambda handler regressions."""

import os
import tempfile
import pytest
from aws_cdk import App
from aws_cdk.assertions import Template, Match
from infra.stacks.emoji_smith_stack import EmojiSmithStack


@pytest.mark.unit
class TestEmojiSmithStack:
    """Test suite for CDK stack configuration."""

    def test_webhook_lambda_handler_path_is_correct(self):
        """Webhook Lambda handler must use simplified entry point for imports."""
        # Arrange
        app = App()

        # Create a temporary webhook package file for testing
        with tempfile.NamedTemporaryFile(
            suffix=".zip", delete=False, dir=os.getcwd()
        ) as temp_file:
            temp_file.write(b"dummy content")
            temp_file.flush()
            # Rename to expected name
            webhook_package_path = os.path.join(os.getcwd(), "webhook_package.zip")
            os.rename(temp_file.name, webhook_package_path)

            try:
                # Act
                stack = EmojiSmithStack(app, "test-stack")

                # Get the CloudFormation template
                template = Template.from_stack(stack)

                # Assert - verify the handler path in the synthesized template
                # Updated to match the simplified handler path that fixes Lambda imports
                template.has_resource_properties(
                    "AWS::Lambda::Function",
                    {"Handler": "webhook_handler.handler"},
                )
            finally:
                # Clean up the temporary file
                if os.path.exists(webhook_package_path):
                    os.remove(webhook_package_path)

    def test_worker_lambda_uses_correct_cmd(self):
        """Worker Lambda container must specify correct handler command."""
        # Arrange
        app = App()
        app.node.set_context(
            "imageUri", "123456789.dkr.ecr.us-east-2.amazonaws.com/emoji-smith:latest"
        )

        # Create a temporary webhook package file for testing
        with tempfile.NamedTemporaryFile(
            suffix=".zip", delete=False, dir=os.getcwd()
        ) as temp_file:
            temp_file.write(b"dummy content")
            temp_file.flush()
            # Rename to expected name
            webhook_package_path = os.path.join(os.getcwd(), "webhook_package.zip")
            os.rename(temp_file.name, webhook_package_path)

            try:
                # Act
                stack = EmojiSmithStack(app, "test-stack")

                # Get the CloudFormation template
                template = Template.from_stack(stack)

                # Assert - verify the worker Lambda has correct CMD in ImageConfig
                template.has_resource_properties(
                    "AWS::Lambda::Function",
                    Match.object_like(
                        {
                            "PackageType": "Image",
                            "ImageConfig": {
                                "Command": [
                                    (
                                        "emojismith.infrastructure.aws."
                                        "worker_handler.handler"
                                    )
                                ]
                            },
                        }
                    ),
                )
            finally:
                # Clean up the temporary file
                if os.path.exists(webhook_package_path):
                    os.remove(webhook_package_path)
