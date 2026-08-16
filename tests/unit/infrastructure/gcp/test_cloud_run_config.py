"""Regression tests for latency-sensitive Cloud Run settings."""

from pathlib import Path


def test_webhook_keeps_one_warm_instance_for_slack_triggers() -> None:
    """Slack trigger IDs can expire before a scale-from-zero startup completes."""
    repo_root = Path(__file__).resolve().parents[4]
    terraform = (repo_root / "terraform" / "cloud_run_webhook.tf").read_text()

    scaling_block = terraform.split("scaling {", maxsplit=1)[1].split("}", maxsplit=1)[
        0
    ]
    assert "min_instance_count = 1" in scaling_block
    assert "min_instance_count = 0" not in scaling_block
