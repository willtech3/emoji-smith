import os
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
                # CDK bootstrap permissions
                iam.PolicyStatement(
                    actions=[
                        "ssm:GetParameter",
                        "ssm:GetParameters",
                    ],
                    resources=[
                        f"arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/*"
                    ],
                ),
                # STS permissions for CDK role assumption
                iam.PolicyStatement(
                    actions=[
                        "sts:AssumeRole",
                    ],
                    resources=[
                        f"arn:aws:iam::{self.account}:role/cdk-*"
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

        # Secrets are now injected as environment variables at deploy time
        # No runtime Secrets Manager access needed

        # Create CloudWatch log groups
        # Note: CDK will auto-generate function names like "EmojiSmithStack-EmojiSmithWebhook[hash]"
        # We'll let Lambda create the log groups automatically to avoid naming conflicts

        # Create webhook Lambda (package deployment for fast cold start)
        # Look for webhook package in common locations
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        webhook_package_path = None
        
        # Try project root first (most common)
        candidate_path = os.path.join(project_root, "webhook_package.zip")
        if os.path.exists(candidate_path):
            webhook_package_path = candidate_path
        else:
            # Try current working directory (for CI/CD contexts)
            candidate_path = os.path.join(os.getcwd(), "webhook_package.zip")
            if os.path.exists(candidate_path):
                webhook_package_path = candidate_path
            else:
                # Fallback to relative path for backwards compatibility
                webhook_package_path = os.path.join(os.path.dirname(__file__), "..", "..", "webhook_package.zip")
        
        self.webhook_lambda = _lambda.Function(
            self,
            "EmojiSmithWebhook",
            code=_lambda.Code.from_asset(webhook_package_path),
            handler="emojismith.infrastructure.aws.webhook_handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            timeout=Duration.seconds(30),  # Fast webhook processing
            memory_size=512,  # Reduced memory for minimal package
            role=lambda_role,
            environment={
                "SQS_QUEUE_URL": self.processing_queue.queue_url,
                "LOG_LEVEL": "INFO",
                # Python optimization flags for better performance
                "PYTHONOPTIMIZE": "1",
                "PYTHONDONTWRITEBYTECODE": "1",
                # Secrets injected at deploy time for performance
                "SLACK_BOT_TOKEN": self.secrets.secret_value_from_json("SLACK_BOT_TOKEN").unsafe_unwrap(),
                "SLACK_SIGNING_SECRET": self.secrets.secret_value_from_json("SLACK_SIGNING_SECRET").unsafe_unwrap(),
            },
        )

        # Provisioned concurrency removed - lazy loading + memory optimization 
        # should achieve sub-3s performance for low-volume usage (8-10 calls/day)
        # without the $9.30/month cost of keeping 3 warm containers

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

        # Secrets are now injected as environment variables at deploy time
        # No runtime Secrets Manager access needed

        # Use same container image for worker Lambda
        worker_lambda_code = _lambda.Code.from_ecr_image(
            repository=ecr.Repository.from_repository_name(
                self, "EmojiSmithWorkerRepository", "emoji-smith"
            ),
            tag_or_digest=image_uri.split(":")[-1],  # Extract tag from URI
            cmd=["emojismith.infrastructure.aws.worker_handler.handler"],
        )

        # Create worker Lambda function
        self.worker_lambda = _lambda.Function(
            self,
            "EmojiSmithWorker",
            code=worker_lambda_code,
            handler=_lambda.Handler.FROM_IMAGE,  # Required for container images
            runtime=_lambda.Runtime.FROM_IMAGE,  # Required for container images
            timeout=Duration.minutes(15),
            memory_size=1024,  # More memory for image processing
            role=worker_lambda_role,
            environment={
                "SQS_QUEUE_URL": self.processing_queue.queue_url,
                "LOG_LEVEL": "INFO",
                # Secrets injected at deploy time for performance
                "SLACK_BOT_TOKEN": self.secrets.secret_value_from_json("SLACK_BOT_TOKEN").unsafe_unwrap(),
                "SLACK_SIGNING_SECRET": self.secrets.secret_value_from_json("SLACK_SIGNING_SECRET").unsafe_unwrap(),
                "OPENAI_API_KEY": self.secrets.secret_value_from_json("OPENAI_API_KEY").unsafe_unwrap(),
                "OPENAI_CHAT_MODEL": self.secrets.secret_value_from_json("OPENAI_CHAT_MODEL").unsafe_unwrap(),
            },
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
