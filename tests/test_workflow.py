from pathlib import Path
import re
import yaml
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def test_trusted_workflow_contract():
    workflow = yaml.load((ROOT / ".github/workflows/security-validation.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"workflow_call"}
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["security-validation"]
    assert job["runs-on"] == "ubuntu-latest"
    for step in job["steps"]:
        if "uses" in step:
            assert re.fullmatch(r"[^@]+@[0-9a-f]{40}", step["uses"])
    central = job["steps"][1]["with"]
    assert central["repository"] == "Ksghld/central-security-workflows-lab"
    assert re.fullmatch("[0-9a-f]{40}", central["ref"])
    commands = "\n".join(step.get("run", "") for step in job["steps"])
    assert "python3 -I controls/scripts/validate.py" in commands
    assert "python3 target/" not in commands
    assert "pip install" not in commands


def test_pinned_controls_match_locally_tested_sources():
    workflow = yaml.load((ROOT / ".github/workflows/security-validation.yml").read_text(), Loader=yaml.BaseLoader)
    pin = workflow["jobs"]["security-validation"]["steps"][1]["with"]["ref"]
    for path in ("scripts/validate.py", "scripts/evidence.py", "scripts/release.py", "policies/default.json", "fixtures/release.json"):
        committed = subprocess.check_output(["git", "show", f"{pin}:{path}"], cwd=ROOT)
        assert committed.replace(b"\r\n", b"\n") == (ROOT / path).read_bytes().replace(b"\r\n", b"\n")
