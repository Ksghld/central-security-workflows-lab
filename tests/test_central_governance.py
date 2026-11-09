import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_codeowners_covers_central_controls():
    lines = (ROOT / ".github/CODEOWNERS").read_text().splitlines()
    entries = dict(line.split(maxsplit=1) for line in lines if line and not line.startswith("#"))
    for path in ("*", "/.github/CODEOWNERS", "/.github/workflows/", "/scripts/", "/policies/", "/fixtures/"):
        assert entries[path] == "@kfise"


def test_central_tests_have_no_privileged_context():
    workflow = yaml.load((ROOT / ".github/workflows/central-controls-tests.yml").read_text(), Loader=yaml.BaseLoader)
    assert set(workflow["on"]) == {"push", "pull_request"}
    assert workflow["permissions"] == {"contents": "read"}
    job = workflow["jobs"]["central-controls-tests"]
    assert job["name"] == "central-controls-tests"
    assert job["runs-on"] == "ubuntu-latest"
    assert job["steps"][0]["with"]["persist-credentials"] == "false"
    assert job["steps"][0]["with"]["fetch-depth"] == "0"
    assert "secrets" not in str(workflow)


def test_central_initial_rules_do_not_invent_a_check():
    proposed = json.loads((ROOT / "docs/governance/main-ruleset.proposed.json").read_text())
    assert proposed["conditions"] == {"ref_name": {"include": ["refs/heads/main"], "exclude": []}}
    assert proposed["enforcement"] == "active"
    assert proposed["bypass_actors"] == []
    rules = {rule["type"]: rule for rule in proposed["rules"]}
    assert "required_status_checks" not in rules
    pr = rules["pull_request"]["parameters"]
    assert pr["required_approving_review_count"] == 1
    assert pr["dismiss_stale_reviews_on_push"] is True
    assert pr["require_last_push_approval"] is True
    assert pr["require_code_owner_review"] is True
    assert {"deletion", "non_fast_forward"} <= set(rules)
