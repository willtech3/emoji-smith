from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_lambda_event_sources as lambda_event_sources,
    aws_apigateway as apigateway,
    aws_sqs as sqs,
    aws_iam as iam,
    aws_secretsmanager as secretsmanager,
    aws_logs as logs,
    aws_ecr as ecr,
)
from constructs import Construct


class EmojiSmithStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        # Get image URI from context (required for container deployment)
        image_uri = self.node.try_get_context("imageUri")
        if not image_uri:
            # Use a placeholder for synth/ls operations, fail only on deploy
            image_uri = "placeholder:latest"

        # Create SQS dead letter queue
        self.processing_dlq = sqs.Queue(
            self,
            "EmojiProcessingDLQ",
            queue_name="emoji-smith-processing-dlq",
            retention_period=Duration.days(14),  # Keep failed messages for 2 weeks
        )

        # Create SQS queue for background processing
        self.processing_queue = sqs.Queue(
            self,
            "EmojiProcessingQueue",
            queue_name="emoji-smith-processing",
            visibility_timeout=Duration.minutes(15),  # Match Lambda timeout
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,  # Retry failed messages 3 times
                queue=self.processing_dlq,
            ),
        )

        # Create IAM user for GitHub Actions deployment
        self.deployment_user = iam.User(
            self,
            "EmojiSmithDeploymentUser",
            user_name="emoji-smith-deployment-user",
        )

        # Grant deployment user least privilege permissions for CDK deployment
        deployment_policy = iam.Policy(
            self,
            "EmojiSmithDeploymentPolicy",
            statements=[
                # CloudFormation permissions for this stack only
                iam.PolicyStatement(
                    actions=[
                        "cloudformation:CreateStack",
                        "cloudformation:UpdateStack",
                        "cloudformation:DeleteStack",
                        "cloudformation:DescribeStacks",
                        "cloudformation:DescribeStackEvents",
                        "cloudformation:DescribeStackResources",
                        "cloudformation:GetTemplate",
                        "cloudformation:ListStacks",
                    ],
                    resources=[
                        f"arn:aws:cloudformation:{self.region}:{self.account}:stack/EmojiSmithStack/*"
                    ],
                ),
                # S3 permissions for CDK assets (CDK creates bucket for deployment artifacts)
                iam.PolicyStatement(
                    actions=[
                        "s3:GetObject",
                        "s3:PutObject",
                        "s3:DeleteObject",
                        "s3:ListBucket",
                        "s3:GetBucketLocation",
                        "s3:CreateBucket",
                    ],
                    resources=[
                        f"arn:aws:s3:::cdk-*-assets-{self.account}-{self.region}",
                        f"arn:aws:s3:::cdk-*-assets-{self.account}-{self.region}/*",
                    ],
                ),
                # ECR permissions for container images
                iam.PolicyStatement(
                    actions=[
                        "ecr:GetAuthorizationToken",
                        "ecr:BatchCheckLayerAvailability",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:BatchGetImage",
                        "ecr:DescribeRepositories",
                        "ecr:CreateRepository",
                        "ecr:PutImage",
                        "ecr:InitiateLayerUpload",
                        "ecr:UploadLayerPart",
                        "ecr:CompleteLayerUpload",
                    ],
                    resources=[
                        f"arn:aws:ecr:{self.region}:{self.account}:repository/emoji-smith"
                    ],
                ),
                # Additional ECR permission that requires wildcard
                iam.PolicyStatement(
                    actions=["ecr:GetAuthorizationToken"],
                    resources=["*"],
                ),
                # Specific IAM permissions for pass role (CDK needs this)
                iam.PolicyStatement(
                    actions=["iam:PassRole"],
                    resources=[
                        f"arn:aws:iam::{self.account}:role/EmojiSmithStack-*"
                    ],
                ),
                # Read-only permissions to check existing resources
                iam.PolicyStatement(
                    actions=[
                        "lambda:GetFunction",
                        "apigateway:GET",
                        "sqs:GetQueueAttributes",
                        "secretsmanager:DescribeSecret",
                        "logs:DescribeLogGroups",
                        "iam:GetRole",
                        "iam:ListRolePolicies",
                        "iam:GetRolePolicy",
                    ],
                    resources=["*"],
                ),
            ],
        )

        self.deployment_user.attach_inline_policy(deployment_policy)

        # Create Secrets Manager for production secrets
        self.secrets = secretsmanager.Secret(
            self,
            "EmojiSmithSecrets",
            secret_name="emoji-smith/production",
            description="Production secrets for Emoji Smith bot",
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template='{"LOG_LEVEL":"INFO"}',
                generate_string_key="generated_password",  # nosec B106
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

        # Create CloudWatch log groups
        webhook_log_group = logs.LogGroup(
            self,
            "EmojiSmithWebhookLogGroup",
            log_group_name="/aws/lambda/emoji-smith-webhook",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        worker_log_group = logs.LogGroup(
            self,
            "EmojiSmithWorkerLogGroup",
            log_group_name="/aws/lambda/emoji-smith-worker",
            retention=logs.RetentionDays.ONE_MONTH,
        )

        # Use container image from ECR
        lambda_code = _lambda.Code.from_ecr_image(
            repository=ecr.Repository.from_repository_name(
                self, "EmojiSmithRepository", "emoji-smith"
            ),
            tag_or_digest=image_uri.split(":")[-1],  # Extract tag from URI
            cmd=["lambda_handler.handler"],
        )

        # Create Lambda function
        self.webhook_lambda = _lambda.Function(
            self,
            "EmojiSmithWebhook",
            function_name="emoji-smith-webhook",
            code=lambda_code,
            handler=_lambda.Handler.FROM_IMAGE,  # Required for container images
            runtime=_lambda.Runtime.FROM_IMAGE,  # Required for container images
            timeout=Duration.minutes(15),
            memory_size=512,
            role=lambda_role,
            environment={
                "SECRETS_NAME": self.secrets.secret_name,
                "SQS_QUEUE_URL": self.processing_queue.queue_url,
                "LOG_LEVEL": "INFO",
            },
            log_group=webhook_log_group,
        )

        # Create worker Lambda role
        worker_lambda_role = iam.Role(
            self,
            "EmojiSmithWorkerLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Grant worker Lambda access to SQS queue
        self.processing_queue.grant_consume_messages(worker_lambda_role)
        self.processing_dlq.grant_consume_messages(worker_lambda_role)

        # Grant worker Lambda access to Secrets Manager
        self.secrets.grant_read(worker_lambda_role)

        # Use same container image for worker Lambda
        worker_lambda_code = _lambda.Code.from_ecr_image(
            repository=ecr.Repository.from_repository_name(
                self, "EmojiSmithWorkerRepository", "emoji-smith"
            ),
            tag_or_digest=image_uri.split(":")[-1],  # Extract tag from URI
            cmd=["worker_handler.handler"],
        )

        # Create worker Lambda function
        self.worker_lambda = _lambda.Function(
            self,
            "EmojiSmithWorker",
            function_name="emoji-smith-worker",
            code=worker_lambda_code,
            handler=_lambda.Handler.FROM_IMAGE,  # Required for container images
            runtime=_lambda.Runtime.FROM_IMAGE,  # Required for container images
            timeout=Duration.minutes(15),
            memory_size=1024,  # More memory for image processing
            role=worker_lambda_role,
            environment={
                "SECRETS_NAME": self.secrets.secret_name,
                "LOG_LEVEL": "INFO",
            },
            log_group=worker_log_group,
        )

        # Create SQS event source for worker Lambda
        self.worker_lambda.add_event_source(
            lambda_event_sources.SqsEventSource(
                self.processing_queue,
                batch_size=1,  # Process one emoji job at a time
                max_batching_window=Duration.seconds(5),
            )
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
                allow_headers=[
                    "Content-Type",
                    "X-Slack-Signature",
                    "X-Slack-Request-Timestamp",
                ],
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
        events_resource.add_resource("interactive").add_method(
            "POST", webhook_integration
        )
