from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
)
from constructs import Construct


class EmojiSmithStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create SQS queue for background processing
        self.processing_queue = sqs.Queue(
            self,
            "EmojiProcessingQueue",
            queue_name="emoji-smith-processing",
            visibility_timeout=Duration.minutes(15),  # Match Lambda timeout
        )

        # Create Secrets Manager for production secrets
        self.secrets = secretsmanager.Secret(
            self,
            "EmojiSmithSecrets",
            secret_name="emoji-smith/production",
            description="Production secrets for Emoji Smith bot",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"LOG_LEVEL":"INFO"}',
                generate_string_key="generated_password",
                exclude_characters='"@/\\',
            ),
        )

        # Create Lambda execution role
        lambda_role = iam.Role(
            self,
            "EmojiSmithLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Grant Lambda access to SQS queue
        self.processing_queue.grant_send_messages(lambda_role)
        self.processing_queue.grant_consume_messages(lambda_role)

        # Grant Lambda access to Secrets Manager
        self.secrets.grant_read(lambda_role)

        # Create CloudWatch log group
        log_group = logs.LogGroup(
            self,
            "EmojiSmithLogGroup",
            log_group_name="/aws/lambda/emoji-smith-webhook",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        # Create Lambda function
        self.webhook_lambda = _lambda.Function(
            self,
            "EmojiSmithWebhook",
            function_name="emoji-smith-webhook",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="lambda_handler.handler",
            code=_lambda.Code.from_asset("../src"),
            timeout=Duration.minutes(15),
            memory_size=512,
            role=lambda_role,
            environment={
                "SECRETS_NAME": self.secrets.secret_name,
                "SQS_QUEUE_URL": self.processing_queue.queue_url,
                "LOG_LEVEL": "INFO",
            },
            log_group=log_group,
        )

        # Create API Gateway for Slack webhooks
        self.api = apigateway.RestApi(
            self,
            "EmojiSmithApi",
            rest_api_name="emoji-smith-webhooks",
            description="API Gateway for Emoji Smith Slack webhooks",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=["*"],
                allow_methods=["GET", "POST"],
                allow_headers=["Content-Type", "X-Slack-Signature", "X-Slack-Request-Timestamp"],
            ),
        )

        # Create Lambda integration
        webhook_integration = apigateway.LambdaIntegration(
            self.webhook_lambda,
            request_templates={"application/json": '{"statusCode": "200"}'},
        )

        # Add health endpoint
        health_resource = self.api.root.add_resource("health")
        health_resource.add_method("GET", webhook_integration)

        # Add webhook endpoint
        webhook_resource = self.api.root.add_resource("webhook")
        webhook_resource.add_method("POST", webhook_integration)

        # Add Slack events endpoint
        events_resource = self.api.root.add_resource("slack")
        events_resource.add_resource("events").add_method("POST", webhook_integration)
        events_resource.add_resource("interactive").add_method("POST", webhook_integration)