import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("evidence", Path(__file__).resolve().parents[1] / "scripts/evidence.py")
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


@pytest.fixture
def records():
    approved = dict(repository="synthetic/sample", repository_id="10001", technical_owner="platform-team")
    registry = {"applications": {"APP-00427": approved}, "approved_release_refs": ["main"]}
    snapshot = {"repository": {"name": "synthetic/sample", "id": "10001"}, "application_id": "APP-00427",
                "metadata": dict(approved, application_id="APP-00427"), "validation_sha": "a" * 40,
                "observed_check_name": "gate / security-validation", "release_branches": ["main"],
                "workflows": [{"on": {"push": None}}, {"on": {"pull_request": {"types": ["opened", "synchronize", "reopened", "ready_for_review"]}}}],
                "effective_rules": [{"enforcement": "active", "targets": ["refs/heads/main"], "required_checks": [{"context": "gate / security-validation", "app_slug": "github-actions"}]}],
                "check_runs": [{"name": "gate / security-validation", "head_sha": "a" * 40, "conclusion": "success", "app_slug": "github-actions"}]}
    return snapshot, registry


def test_complete_offline_snapshot(records):
    assert set(evidence.inspect_inventory(*records).values()) == {"PASS"}


def test_missing_rules_unknown(records):
    del records[0]["effective_rules"]
    assert evidence.inspect_inventory(*records)["effective_ruleset"] == "UNKNOWN"


def test_stale_success_not_pass(records):
    records[0]["validation_sha"] = "b" * 40
    assert evidence.inspect_inventory(*records)["latest_scan"] == "FAIL"


def test_wrong_target(records):
    records[0]["effective_rules"][0]["targets"] = ["refs/heads/other"]
    assert evidence.inspect_inventory(*records)["required_check"] == "FAIL"


def test_wrong_source(records):
    records[0]["effective_rules"][0]["required_checks"][0]["app_slug"] = "other"
    assert evidence.inspect_inventory(*records)["expected_source"] == "FAIL"


def test_unknown_release(records):
    records[0]["release_branches"] = ["unapproved"]
    assert evidence.inspect_inventory(*records)["release_branches"] == "FAIL"


def test_newer_failed_attempt_overrides_success(records):
    runs = records[0]["check_runs"]
    runs[0]["id"] = 10
    runs.insert(0, dict(runs[0], id=11, conclusion="failure"))
    assert evidence.inspect_inventory(*records)["latest_scan"] == "FAIL"


def test_ambiguous_attempt_order_is_unknown(records):
    records[0]["check_runs"].append(dict(records[0]["check_runs"][0]))
    assert evidence.inspect_inventory(*records)["latest_scan"] == "UNKNOWN"
