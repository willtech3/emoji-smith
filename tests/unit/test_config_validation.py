import json
from pathlib import Path


def test_infra_cdk_json_valid() -> None:
    """Validate required keys in infra/cdk.json."""
    config_path = Path("infra/cdk.json")
    data = json.loads(config_path.read_text())

    assert data["app"] == "python app.py"
    assert "context" in data
    assert isinstance(data["context"], dict)
    assert "@aws-cdk/aws-lambda:useLatestRuntimeVersion" in data["context"]
