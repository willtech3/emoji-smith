"""Test CDK stack configuration to prevent Lambda handler regressions."""

from unittest.mock import patch
from aws_cdk import App
from aws_cdk.assertions import Template, Match
from infra.stacks.emoji_smith_stack import EmojiSmithStack


class TestEmojiSmithStack:
    """Test suite for CDK stack configuration."""

    def test_webhook_lambda_handler_path_is_correct(self):
        """Webhook Lambda handler must use correct module path."""
        # Arrange
        app = App()

        # Mock the file existence checks to avoid file system dependencies
        with patch("os.path.exists", return_value=True):
            # Act
            stack = EmojiSmithStack(app, "test-stack")

            # Get the CloudFormation template
            template = Template.from_stack(stack)

            # Assert - verify the handler path in the synthesized template
            template.has_resource_properties(
                "AWS::Lambda::Function",
                {"Handler": "emojismith.infrastructure.aws.webhook_handler.handler"},
            )

    def test_worker_lambda_uses_correct_cmd(self):
        """Worker Lambda container must specify correct handler command."""
        # Arrange
        app = App()
        app.node.set_context(
            "imageUri", "123456789.dkr.ecr.us-east-2.amazonaws.com/emoji-smith:latest"
        )

        # Mock the file existence for webhook package
        with patch("os.path.exists", return_value=True):
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
                                "emojismith.infrastructure.aws.worker_handler.handler"
                            ]
                        },
                    }
                ),
            )
