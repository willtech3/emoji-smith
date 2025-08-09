"""Integration tests for Lambda package structure."""

import subprocess
import tempfile
import zipfile
from pathlib import Path

import pytest


class TestLambdaPackage:
    """Test Lambda package can be imported correctly."""

    @pytest.mark.integration()
    def test_webhook_handler_importable(self):
        """Ensure Lambda handler can be imported as expected by AWS."""
        # Build the webhook package
        project_root = Path(__file__).parent.parent.parent
        build_script = project_root / "scripts" / "build_webhook_package.sh"

        result = subprocess.run(
            [str(build_script)], cwd=project_root, capture_output=True, text=True
        )

        assert result.returncode == 0, f"Build failed: {result.stderr}"

        # Verify package exists
        package_path = project_root / "webhook_package.zip"
        assert package_path.exists(), "webhook_package.zip not created"

        # Extract and test import
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(package_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Test import in subprocess to avoid polluting test environment
            test_code = f"""
import sys
import os
sys.path.insert(0, r'{temp_dir}')
# Set required environment variables for boto3
os.environ['AWS_DEFAULT_REGION'] = 'us-east-2'
os.environ['SLACK_BOT_TOKEN'] = 'dummy'
os.environ['SLACK_SIGNING_SECRET'] = 'dummy'
os.environ['SQS_QUEUE_URL'] = 'dummy'
import webhook_handler
assert hasattr(webhook_handler, 'handler')
print('Handler import successful')
"""

            result = subprocess.run(
                ["python3", "-c", test_code], capture_output=True, text=True
            )

            assert result.returncode == 0, f"Import failed: {result.stderr}"
            assert "Handler import successful" in result.stdout

    @pytest.mark.integration()
    def test_webhook_package_structure(self):
        """Verify webhook package has correct structure."""
        project_root = Path(__file__).parent.parent.parent
        package_path = project_root / "webhook_package.zip"

        # Build package if it doesn't exist
        if not package_path.exists():
            build_script = project_root / "scripts" / "build_webhook_package.sh"
            subprocess.run([str(build_script)], cwd=project_root, check=True)

        with zipfile.ZipFile(package_path, "r") as zip_ref:
            files = zip_ref.namelist()

            # Check critical files exist
            assert "webhook_handler.py" in files, "Missing top-level handler"
            assert "emojismith/infrastructure/aws/webhook_handler.py" in files
            assert "shared/" in " ".join(files), "Missing shared module"
            assert "secrets_loader.py" in files

            # Check dependencies are included
            assert any("mangum" in f for f in files), "Missing mangum dependency"
            assert any("fastapi" in f for f in files), "Missing fastapi dependency"
            assert any("slack_sdk" in f for f in files), "Missing slack_sdk dependency"
