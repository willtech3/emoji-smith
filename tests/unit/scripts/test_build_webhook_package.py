import pytest


def test_script_includes_shared_copy():
    script_path = "scripts/build_webhook_package.sh"
    with open(script_path) as f:
        content = f.read()
    assert (
        "src/shared" in content
    ), "webhook package script should include shared module"
