"""Offline coverage and synthetic provenance checks; never queries an organization."""
import argparse
import csv
import json
from pathlib import Path


def coverage(record):
    checks = {}
    for key in ("repository_identity", "push_trigger", "pr_trigger", "effective_ruleset",
                "required_check", "expected_source", "latest_scan", "release_branches", "ownership"):
        value = record.get(key)
        checks[key] = "PASS" if value is True else "FAIL" if value is False else "NOT_APPLICABLE" if value == "NOT_APPLICABLE" else "UNKNOWN"
    return checks


def correlate(expected, observed):
    fields = ("application_id", "repository_id", "commit_sha", "build_id", "artifact_digest",
              "deployment_id", "cloud_resource_id", "runtime_digest")
    missing = [key for key in fields if not expected.get(key) or not observed.get(key)]
    mismatches = [key for key in fields if expected.get(key) != observed.get(key)]
    if observed.get("runtime_digest") != observed.get("artifact_digest"):
        mismatches.append("runtime_artifact_digest")
    return {"result": "UNKNOWN" if missing else "FAIL" if mismatches else "PASS",
            "missing": missing, "mismatches": mismatches, "synthetic": True,
            "verified_deployment_provenance": False}


def inspect_inventory(snapshot, registry):
    """Evaluate sanitized offline API/workflow evidence, without network access."""
    repository = snapshot.get("repository")
    if not repository:
        return coverage({})
    approved = registry.get("applications", {}).get(snapshot.get("application_id"))
    identity = bool(approved and repository.get("id") == approved.get("repository_id")
                    and repository.get("name") == approved.get("repository"))
    result = {"repository_identity": identity}
    workflows = snapshot.get("workflows")
    if workflows is not None:
        result["push_trigger"] = any(w.get("on", {}).get("push", "missing") in (None, "", {}) for w in workflows)
        required_events = {"opened", "synchronize", "reopened", "ready_for_review"}
        result["pr_trigger"] = any(required_events <= set(w.get("on", {}).get("pull_request", {}).get("types", [])) for w in workflows)
    rules = snapshot.get("effective_rules")
    check = snapshot.get("observed_check_name")
    if rules is not None:
        active = [r for r in rules if r.get("enforcement") == "active" and "refs/heads/main" in r.get("targets", [])]
        result["effective_ruleset"] = bool(active)
        if check:
            checks = [c for r in active for c in r.get("required_checks", []) if c.get("context") == check]
            result["required_check"] = bool(checks)
            result["expected_source"] = bool(checks and all(c.get("app_slug") == "github-actions" for c in checks))
    runs = snapshot.get("check_runs")
    sha = snapshot.get("validation_sha")
    if runs is not None and sha and check:
        matching = [r for r in runs if r.get("name") == check and r.get("head_sha") == sha]
        # Multiple attempts need ordering evidence; never pick a convenient green run.
        if len(matching) > 1 and not all(isinstance(r.get("id"), int) for r in matching):
            result["latest_scan"] = None
        else:
            latest = max(matching, key=lambda r: r.get("id", 0)) if matching else {}
            result["latest_scan"] = bool(latest.get("conclusion") == "success"
                                         and latest.get("app_slug") == "github-actions")
    branches = snapshot.get("release_branches")
    if branches is not None and approved and "approved_release_refs" in registry:
        result["release_branches"] = bool(branches) and set(branches) <= set(registry["approved_release_refs"])
    metadata = snapshot.get("metadata")
    if metadata is not None:
        result["ownership"] = bool(identity and metadata == dict(approved, application_id=snapshot.get("application_id")))
    return coverage(result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--registry", type=Path)
    args = parser.parse_args()
    snapshot = json.loads(args.fixture.read_text())
    result = inspect_inventory(snapshot, json.loads(args.registry.read_text())) if args.registry else coverage(snapshot)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "coverage.json").write_text(json.dumps(result, indent=2))
    with (args.output / "coverage.csv").open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["control", "status"])
        writer.writerows(result.items())
    (args.output / "coverage.md").write_text("| Control | Status |\n| --- | --- |\n" + "".join(f"| {k} | {v} |\n" for k, v in result.items()))


if __name__ == "__main__":
    main()
