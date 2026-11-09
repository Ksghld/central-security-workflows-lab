"""Static trust-boundary checks; no GitHub calls or synthetic deployment."""
from pathlib import Path
import re

import yaml

ROOT = Path(__file__).resolve().parents[1]


def workflow(name):
    return yaml.load((ROOT / ".github/workflows" / name).read_text(), Loader=yaml.BaseLoader)


def test_build_has_only_required_write_permissions():
    build = workflow("release-build.yml")
    assert set(build["on"]) == {"workflow_call"}
    assert build["permissions"] == {"contents": "read", "actions": "read", "pull-requests": "read",
                                     "id-token": "write", "attestations": "write"}
    job = build["jobs"]["build"]
    assert "refs/heads/main" in job["if"]
    assert "github.event.workflow_run.head_sha == github.sha" in job["if"]
    steps = job["steps"]
    commands = "\n".join(step.get("run", "") for step in steps)
    assert "python3 source/" not in commands
    assert "pip install" not in commands
    upload = next(i for i, step in enumerate(steps) if step.get("id") == "release")
    attest = next(i for i, step in enumerate(steps) if step.get("id") == "attest")
    assert upload < attest
    assert steps[attest]["with"]["subject-path"].split() == ["out/release.zip", "out/release-record.json"]
    assert steps[attest]["with"]["create-storage-record"] == "false"
    assert steps[attest]["with"]["push-to-registry"] == "false"


def test_verifier_cannot_sign_and_never_checks_out_application():
    verify = workflow("release-verify.yml")
    assert set(verify["on"]) == {"workflow_call"}
    assert set(verify["permissions"].values()) == {"read"}
    assert "id-token" not in verify["permissions"]
    job = verify["jobs"]["verify"]
    assert "refs/heads/main" in job["if"]
    assert re.fullmatch("[0-9a-f]{40}", job["env"]["SIGNER_SHA"])
    checkouts = [step for step in job["steps"] if step.get("uses", "").startswith("actions/checkout@")]
    assert len(checkouts) == 1
    assert checkouts[0]["with"]["repository"] == "Ksghld/central-security-workflows-lab"
    assert re.fullmatch("[0-9a-f]{40}", checkouts[0]["with"]["ref"])
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "${{" not in commands
    assert "--fault" in commands
    assert "continue-on-error" not in str(verify)


def test_release_actions_are_pinned_and_have_short_retention():
    for name in ("release-build.yml", "release-verify.yml"):
        data = workflow(name)
        assert "secrets" not in data["on"]["workflow_call"] if isinstance(data["on"]["workflow_call"], dict) else True
        for job in data["jobs"].values():
            assert job["runs-on"] == "ubuntu-latest"
            assert job["timeout-minutes"] == "10"
            for step in job["steps"]:
                if "uses" not in step:
                    continue
                action, pin = step["uses"].split("@")
                assert re.fullmatch("[0-9a-f]{40}", pin)
                if action == "actions/upload-artifact":
                    assert step["with"]["retention-days"] == "7"
                    assert step["with"]["if-no-files-found"] == "error"
                if action == "actions/checkout":
                    assert step["with"]["persist-credentials"] == "false"
