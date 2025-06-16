"""AWS Lambda handler for Emoji Smith."""

import json
import os
import boto3
from typing import Dict, Any
from mangum import Mangum
from emojismith.app import create_app


def _load_secrets_from_aws() -> None:
    """Load secrets from AWS Secrets Manager into environment variables."""
    secrets_name = os.environ.get("SECRETS_NAME")
    if not secrets_name:
        return
    
    try:
        secrets_client = boto3.client("secretsmanager")
        response = secrets_client.get_secret_value(SecretId=secrets_name)
        secrets = json.loads(response["SecretString"])
        
        # Set environment variables from secrets
        for key, value in secrets.items():
            if key != "generated_password":  # Skip auto-generated password
                os.environ[key] = value
    except Exception as e:
        print(f"Warning: Could not load secrets from AWS: {e}")


# Load secrets when module is imported
_load_secrets_from_aws()

# Create FastAPI app
app = create_app()

# Create Lambda handler using Mangum
handler = Mangum(app, lifespan="off")