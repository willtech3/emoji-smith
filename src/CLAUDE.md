# CLAUDE.md - Security Guidelines

## Inheritance
- **Extends:** /CLAUDE.md (root)
- **Overrides:** None (CRITICAL RULES cannot be overridden)
- **Scope:** All source code files in src directory and subdirectories

## Rules

**Context:** This document provides security guidelines that apply across all source code. Read this when reviewing security practices, handling secrets, or implementing authentication/authorization.

## 🔐 Security Principles

1. **Defense in Depth**: Multiple layers of security controls
2. **Least Privilege**: Grant minimum required permissions
3. **Zero Trust**: Verify everything, trust nothing
4. **Secure by Default**: Security isn't optional

## Secret Management

### Development Environment

#### Using .env Files
```bash
# .env.example (commit this)
SLACK_BOT_TOKEN=xoxb-your-token-here
OPENAI_API_KEY=sk-your-key-here
AWS_REGION=us-east-1

# .env (NEVER commit this)
SLACK_BOT_TOKEN=xoxb-actual-token-value
OPENAI_API_KEY=sk-actual-api-key
AWS_REGION=us-east-1
```

#### Git Security
```bash
# ✅ CORRECT - Explicit file specification
git add src/emojismith/new_feature.py tests/unit/test_new_feature.py

# ❌ WRONG - Could accidentally commit secrets
git add .
git add -A
git add *
```

### Production Environment

#### AWS Secrets Manager
```python
import boto3
import json
from functools import lru_cache

@lru_cache()
def get_secrets() -> dict:
    """Retrieve secrets from AWS Secrets Manager."""
    client = boto3.client('secretsmanager')

    try:
        response = client.get_secret_value(SecretId='emoji-smith/prod')
        return json.loads(response['SecretString'])
    except Exception as e:
        logger.error(f"Failed to retrieve secrets: {e}")
        raise

# Usage
secrets = get_secrets()
slack_token = secrets['SLACK_BOT_TOKEN']
openai_key = secrets['OPENAI_API_KEY']
```

#### Environment Variable Security
```python
# ❌ WRONG - Hardcoded secrets
API_KEY = "sk-1234567890abcdef"
DATABASE_URL = "postgresql://user:pass@host/db"

# ❌ WRONG - Logged secrets
logger.info(f"Using API key: {api_key}")

# ✅ CORRECT - Safe loading
api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable required")

# ✅ CORRECT - Masked logging
logger.info(f"Using API key: {'*' * 8}{api_key[-4:]}")
```

## Authentication & Authorization

### Slack Request Verification
```python
import hmac
import hashlib
import time

def verify_slack_request(
    signature: str,
    timestamp: str,
    body: bytes,
    signing_secret: str
) -> bool:
    """Verify request is from Slack."""
    # Check timestamp to prevent replay attacks
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Verify signature
    sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    expected_sig = 'v0=' + hmac.new(
        signing_secret.encode(),
        sig_basestring.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_sig, signature)
```

### API Key Rotation
```python
class APIKeyManager:
    """Manage API key rotation."""

    def __init__(self, secrets_client):
        self._client = secrets_client
        self._cache = {}
        self._last_refresh = {}

    async def get_api_key(self, service: str) -> str:
        """Get current API key with automatic refresh."""
        now = time.time()
        last_refresh = self._last_refresh.get(service, 0)

        # Refresh every hour
        if now - last_refresh > 3600:
            self._cache[service] = await self._fetch_key(service)
            self._last_refresh[service] = now

        return self._cache[service]
```

## Input Validation

### Sanitize User Input
```python
import re
from typing import Optional

def sanitize_emoji_description(description: str) -> Optional[str]:
    """Sanitize user-provided emoji description."""
    # Remove potential injection attempts
    cleaned = re.sub(r'[<>\"\'&]', '', description)

    # Limit length
    if len(cleaned) > 500:
        cleaned = cleaned[:500]

    # Remove multiple spaces
    cleaned = ' '.join(cleaned.split())

    # Reject if only special characters remain
    if not cleaned or not any(c.isalnum() for c in cleaned):
        return None

    return cleaned
```

### File Upload Validation
```python
ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_image_upload(file_data: bytes, filename: str) -> bool:
    """Validate uploaded image files."""
    # Check file size
    if len(file_data) > MAX_FILE_SIZE:
        raise ValueError("File too large")

    # Check extension
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(f"Invalid file type: {ext}")

    # Verify file content matches extension
    import imghdr
    file_type = imghdr.what(None, file_data)
    if not file_type or f".{file_type}" != ext:
        raise ValueError("File content doesn't match extension")

    return True
```

## AWS Security

### IAM Best Practices

#### Lambda Execution Role
```python
# CDK example - Least privilege policy
from aws_cdk import aws_iam as iam

lambda_role = iam.Role(
    self, "LambdaRole",
    assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
    managed_policies=[
        iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AWSLambdaBasicExecutionRole"
        )
    ]
)

# Grant specific permissions
queue.grant_send_messages(webhook_lambda_role)
queue.grant_consume_messages(worker_lambda_role)
bucket.grant_read_write(worker_lambda_role)
secrets.grant_read(lambda_role)
```

#### S3 Bucket Security
```python
from aws_cdk import aws_s3 as s3

emoji_bucket = s3.Bucket(
    self, "EmojiBucket",
    encryption=s3.BucketEncryption.S3_MANAGED,
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    versioned=True,
    lifecycle_rules=[
        s3.LifecycleRule(
            id="DeleteOld",
            expiration=Duration.days(90),
            noncurrent_version_expiration=Duration.days(30)
        )
    ]
)

# Bucket policy - restrict to specific Lambda
bucket_policy = iam.PolicyStatement(
    effect=iam.Effect.ALLOW,
    principals=[lambda_role],
    actions=["s3:GetObject", "s3:PutObject"],
    resources=[f"{emoji_bucket.bucket_arn}/*"],
    conditions={
        "StringEquals": {
            "s3:x-amz-server-side-encryption": "AES256"
        }
    }
)
```

### Network Security

#### VPC Configuration (if required)
```python
# Place Lambda in private subnet
vpc = ec2.Vpc(self, "SecureVPC",
    subnet_configuration=[
        ec2.SubnetConfiguration(
            name="Private",
            subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
            cidr_mask=24
        )
    ]
)

# Security group - restrict outbound
security_group = ec2.SecurityGroup(
    self, "LambdaSG",
    vpc=vpc,
    description="Lambda security group",
    allow_all_outbound=False
)

# Allow HTTPS only
security_group.add_egress_rule(
    peer=ec2.Peer.any_ipv4(),
    connection=ec2.Port.tcp(443),
    description="Allow HTTPS outbound"
)
```

## Security Scanning

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/Yelp/detect-secrets
    rev: v1.4.0
    hooks:
      - id: detect-secrets
        args: ['--baseline', '.secrets.baseline']

  # Security checks are now included in ruff
  # Configure security rules in pyproject.toml [tool.ruff.lint]
```

### Ruff Security Scanning
```bash
# Security checks are integrated into ruff
ruff check src/ tests/

# Security-specific rules are prefixed with 'S' (from flake8-bandit)
# Configure in pyproject.toml:
# [tool.ruff.lint]
# select = ["S"]  # Include security rules
# ignore = ["S101", "S104"]  # Skip specific checks with documentation
```

### Dependency Scanning
```bash
# Check for vulnerable dependencies
pip-audit

# Update dependencies safely
pip-audit --fix

# Generate requirements with hashes
pip-compile --generate-hashes requirements.in
```

## Logging Security

### Safe Logging Practices
```python
import logging
from typing import Any

class SecurityLogger:
    """Logger that redacts sensitive information."""

    SENSITIVE_FIELDS = {
        'password', 'token', 'api_key', 'secret',
        'authorization', 'x-api-key'
    }

    @staticmethod
    def redact_dict(data: dict) -> dict:
        """Redact sensitive fields from dictionary."""
        redacted = {}

        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in SecurityLogger.SENSITIVE_FIELDS):
                redacted[key] = "***REDACTED***"
            elif isinstance(value, dict):
                redacted[key] = SecurityLogger.redact_dict(value)
            else:
                redacted[key] = value

        return redacted

    def log_request(self, event: dict) -> None:
        """Safely log API request."""
        safe_event = self.redact_dict(event)
        logger.info(f"Processing request: {safe_event}")
```

### Audit Logging
```python
from datetime import datetime
import json

class AuditLogger:
    """Log security-relevant events."""

    def __init__(self, log_group: str):
        self.log_group = log_group

    async def log_access(
        self,
        user_id: str,
        action: str,
        resource: str,
        result: str
    ) -> None:
        """Log access attempt."""
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "action": action,
            "resource": resource,
            "result": result,
            "ip_address": self._get_client_ip(),
            "user_agent": self._get_user_agent()
        }

        # Send to CloudWatch
        await self._send_to_cloudwatch(audit_entry)
```

## Error Handling

### Secure Error Messages
```python
# ❌ WRONG - Exposes internal details
try:
    connection = psycopg2.connect(database_url)
except Exception as e:
    return {"error": str(e)}  # Might expose connection strings!

# ✅ CORRECT - Generic error for users, detailed for logs
try:
    connection = psycopg2.connect(database_url)
except Exception as e:
    logger.error(f"Database connection failed: {e}")
    return {"error": "Service temporarily unavailable"}
```

## Security Checklist

### Before Every Commit
- [ ] No hardcoded secrets in code
- [ ] No sensitive data in logs
- [ ] Input validation implemented
- [ ] Error messages don't leak information
- [ ] Dependencies are up to date
- [ ] Security scan passes (ruff check)

### Before Deployment
- [ ] Secrets rotated recently
- [ ] IAM policies reviewed (least privilege)
- [ ] S3 buckets not public
- [ ] CloudWatch alarms configured
- [ ] Penetration testing completed (if applicable)
- [ ] Security documentation updated

## Incident Response

### If Secrets Are Exposed
1. **Immediately rotate** the exposed secret
2. **Audit logs** for unauthorized usage
3. **Update** all systems using the secret
4. **Document** the incident and timeline
5. **Review** how exposure occurred
6. **Implement** preventive measures

### Security Contact
- Security Team: security@yourcompany.com
- On-call: Use PagerDuty
- AWS Support: Premium support tier

## Quick Reference

**Never:**
- Hardcode secrets in code
- Log sensitive information
- Trust user input
- Use `git add .`
- Ignore security warnings
- Deploy without security review

**Always:**
- Use AWS Secrets Manager
- Validate all inputs
- Encrypt data in transit and at rest
- Follow least privilege principle
- Keep dependencies updated
- Monitor for anomalies