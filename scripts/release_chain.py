"""Manual/Actions release evidence exercise; no cloud or application execution.

Only gh verifies signatures. Fixture-shaped JSON alone can never authorize release.
All API operations are reads. Errors expose categories, not API responses or tokens.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import zipfile

APP = "Ksghld/secure-code-controls-lab"
CENTRAL = "Ksghld/central-security-workflows-lab"
APP_ID = 1444026417
BUILD_PATH = ".github/workflows/lab-release-build.yml"
SIGNER = CENTRAL + "/.github/workflows/release-build.yml"
MAX_BYTES = 8 * 1024 * 1024
FAULTS = ("none", "tampered-bytes", "missing-record", "wrong-source", "wrong-attempt")


class GateError(Exception):
    pass


def require(condition, code):
    if not condition:
        raise GateError(code)


def sha(value):
    require(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{40}", value), "INVALID_SOURCE_SHA")
    return value


def number(value):
    require(re.fullmatch(r"[1-9][0-9]{0,19}", str(value)) is not None, "INVALID_NUMERIC_ID")
    return int(value)


def command(args, category):
    result = subprocess.run(args, capture_output=True, timeout=120, check=False)
    require(result.returncode == 0, category)
    require(len(result.stdout) <= MAX_BYTES, "RESPONSE_TOO_LARGE")
    return result.stdout


def api(repo, path):
    require(repo in (APP, CENTRAL), "REPOSITORY_DENIED")
    return json.loads(command(["gh", "api", "--method", "GET", f"repos/{repo}/{path}"], "GITHUB_READ_FAILED"))


def governance(repo, expected_check):
    listing = api(repo, "rulesets?includes_parents=false&per_page=100")
    require(len(listing) < 100, "RULESET_PAGINATION_REQUIRED")
    candidates = []
    for item in listing:
        if item.get("enforcement") != "active":
            continue
        rule = api(repo, f"rulesets/{number(item['id'])}")
        if rule.get("conditions") == {"ref_name": {"include": ["refs/heads/main"], "exclude": []}}:
            candidates.append(rule)
    for ruleset in candidates:
        rules = {rule["type"]: rule for rule in ruleset["rules"]}
        pr = rules.get("pull_request", {}).get("parameters", {})
        status = rules.get("required_status_checks", {}).get("parameters", {})
        checks = status.get("required_status_checks", [])
        if (not ruleset.get("bypass_actors") and {"deletion", "non_fast_forward"} <= set(rules)
                and pr.get("required_approving_review_count", 0) >= 1
                and all(pr.get(key) is True for key in ("require_code_owner_review", "dismiss_stale_reviews_on_push", "require_last_push_approval"))
                and status.get("strict_required_status_checks_policy") is True
                and {"context": expected_check, "integration_id": 15368} in checks):
            return
    raise GateError("ACTIVE_CODEOWNER_RULESET_REQUIRED")


def approved_source(source_sha):
    require(api(APP, "git/ref/heads/main")["object"]["sha"] == source_sha, "SOURCE_NOT_CURRENT_MAIN")
    prs = api(APP, f"commits/{source_sha}/pulls?per_page=100")
    require(len(prs) < 100, "PR_PAGINATION_REQUIRED")
    for pr in prs:
        if not (pr.get("merged_at") and pr.get("merge_commit_sha") == source_sha and pr["base"]["ref"] == "main"):
            continue
        reviews = api(APP, f"pulls/{number(pr['number'])}/reviews?per_page=100")
        require(len(reviews) < 100, "REVIEW_PAGINATION_REQUIRED")
        latest = {}
        for review in reviews:
            if review["state"] != "COMMENTED":
                latest[review["user"]["login"]] = review
        owner = latest.get("kfise", {})
        if (pr["user"]["login"] != "kfise" and owner.get("state") == "APPROVED"
                and owner.get("commit_id") == pr["head"]["sha"]):
            break
    else:
        raise GateError("INDEPENDENT_MERGED_APPROVAL_REQUIRED")
    checks = api(APP, f"commits/{source_sha}/check-runs?per_page=100")
    require(checks["total_count"] < 100, "CHECK_PAGINATION_REQUIRED")
    release = [check for check in checks["check_runs"]
               if check["name"] == "appsec-release-verify / security-validation"
               and check["app"]["id"] == 15368 and check["head_sha"] == source_sha]
    require(bool(release), "POSTMERGE_CHECK_MISSING")
    newest = max(release, key=lambda check: check["id"])
    require(newest["conclusion"] == "success", "POSTMERGE_CHECK_NOT_SUCCESSFUL")


def protected_context(source_sha, controls_sha):
    sha(source_sha)
    sha(controls_sha)
    governance(APP, "appsec-pr-gate / security-validation")
    governance(CENTRAL, "central-controls-tests")
    comparison = api(CENTRAL, f"compare/{controls_sha}...main")
    require(comparison["status"] in ("ahead", "identical"), "CONTROLS_NOT_MERGED")
    approved_source(source_sha)


def build(target, destination, source_sha):
    sha(source_sha)
    actual = command(["git", "-C", str(target), "rev-parse", "HEAD"], "CHECKOUT_READ_FAILED").decode().strip()
    require(actual == source_sha, "CHECKOUT_SHA_MISMATCH")
    root = target / "src"
    require(root.is_dir() and not root.is_symlink(), "SOURCE_DIRECTORY_INVALID")
    files = sorted(root.rglob("*"))
    require(0 < len(files) <= 100 and any(file.is_file() for file in files), "SOURCE_FILE_COUNT_INVALID")
    destination.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in files:
            require(not file.is_symlink(), "SOURCE_SYMLINK_DENIED")
            if file.is_dir():
                continue
            require(file.is_file() and file.suffix == ".txt", "SOURCE_FILE_TYPE_DENIED")
            require(file.stat().st_size <= MAX_BYTES, "SOURCE_TOO_LARGE")
            data = file.read_bytes()
            total += len(data)
            require(total <= MAX_BYTES, "SOURCE_TOO_LARGE")
            entry = zipfile.ZipInfo(file.relative_to(target).as_posix(), (2020, 1, 1, 0, 0, 0))
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
        entry = zipfile.ZipInfo("source.json", (2020, 1, 1, 0, 0, 0))
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, json.dumps({"repository": APP, "source_sha": source_sha, "payload": "synthetic"}, sort_keys=True))
    print("RELEASE_FILE_BUILT=PASS")


def digest(file):
    require(file.is_file() and not file.is_symlink() and file.stat().st_size <= MAX_BYTES, "RELEASE_FILE_INVALID")
    return hashlib.sha256(file.read_bytes()).hexdigest()


def artifact_name(kind, source_sha, run_id, attempt):
    return f"{kind}-{source_sha}-{number(run_id)}-{number(attempt)}"


def record(file, destination, source_sha, artifact_id, run_id, attempt):
    result = {"schema": 1, "repository": APP, "source_sha": sha(source_sha), "run_id": number(run_id),
              "run_attempt": number(attempt), "artifact_id": number(artifact_id), "file": "release.zip",
              "sha256": digest(file), "payload": "synthetic", "evidence": "github-actions-live"}
    destination.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("RELEASE_RECEIPT_CREATED=PASS")


def validate_run(run, run_id):
    require(run["id"] == number(run_id), "BUILD_RUN_ID_MISMATCH")
    require(run["repository"]["full_name"] == APP and run["head_repository"]["id"] == APP_ID, "BUILD_REPOSITORY_MISMATCH")
    require(run["path"] == BUILD_PATH and run["name"] == "lab-release-build", "BUILD_WORKFLOW_MISMATCH")
    require(run["head_branch"] == "main" and run["event"] in ("workflow_run", "workflow_dispatch"), "BUILD_EVENT_DENIED")
    require(run["status"] == "completed" and run["conclusion"] == "success", "BUILD_NOT_SUCCESSFUL")
    return sha(run["head_sha"]), number(run["run_attempt"])


def select_artifact(items, name, run_id, source_sha):
    found = [item for item in items if item["name"] == name]
    require(len(found) == 1, "ARTIFACT_MISSING_OR_AMBIGUOUS")
    item = found[0]
    require(item.get("expired") is False and 0 < item["size_in_bytes"] <= MAX_BYTES, "ARTIFACT_EXPIRED_OR_TOO_LARGE")
    require(item["workflow_run"]["id"] == run_id and item["workflow_run"]["head_sha"] == source_sha, "ARTIFACT_RUN_MISMATCH")
    return item


def extract_one(data, filename):
    require(len(data) <= MAX_BYTES, "ARTIFACT_TOO_LARGE")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        entries = archive.infolist()
        require(len(entries) == 1 and entries[0].filename == filename, "ARTIFACT_LAYOUT_INVALID")
        info = entries[0]
        require(info.file_size <= MAX_BYTES and not info.is_dir() and (info.external_attr >> 16) & 0o170000 != 0o120000, "ARTIFACT_ENTRY_INVALID")
        return archive.read(info)


def download(item, filename, work):
    data = command(["gh", "api", "--method", "GET", f"repos/{APP}/actions/artifacts/{number(item['id'])}/zip"], "ARTIFACT_DOWNLOAD_FAILED")
    file = work / filename
    file.write_bytes(extract_one(data, filename))
    return file


def validate_verified_result(results, file_sha, source_sha, run_id, attempt):
    invocation = f"https://github.com/{APP}/actions/runs/{run_id}/attempts/{attempt}"
    for result in results:
        verified = result.get("verificationResult", {})
        cert = verified.get("signature", {}).get("certificate", {})
        statement = verified.get("statement", {})
        if (cert.get("runInvocationURI") == invocation
                and cert.get("sourceRepositoryDigest") == source_sha
                and cert.get("sourceRepositoryURI") == f"https://github.com/{APP}"
                and cert.get("runnerEnvironment") == "github-hosted"
                and statement.get("predicateType") == "https://slsa.dev/provenance/v1"
                and any(subject.get("digest", {}).get("sha256") == file_sha for subject in statement.get("subject", []))):
            return
    raise GateError("VERIFIED_CERTIFICATE_BINDING_MISMATCH")


def verify_signature(file, source_sha, controls_sha, run_id, attempt):
    # No caller-supplied bundle, root, identity, predicate or verification result.
    verified = command(["gh", "attestation", "verify", str(file), "--repo", APP,
                        "--signer-workflow", SIGNER, "--signer-digest", controls_sha,
                        "--source-digest", source_sha, "--source-ref", "refs/heads/main",
                        "--deny-self-hosted-runners", "--predicate-type", "https://slsa.dev/provenance/v1",
                        "--format", "json"], "ATTESTATION_VERIFICATION_FAILED")
    validate_verified_result(json.loads(verified), digest(file), source_sha, run_id, attempt)


def validate_receipt(receipt, file, source_sha, artifact_id, run_id, attempt):
    expected = {"schema": 1, "repository": APP, "source_sha": source_sha, "run_id": run_id,
                "run_attempt": attempt, "artifact_id": artifact_id, "file": "release.zip",
                "sha256": digest(file), "payload": "synthetic", "evidence": "github-actions-live"}
    for key, value in expected.items():
        require(receipt.get(key) == value, f"RECEIPT_{key.upper()}_MISMATCH")


def verify_release(run_id, controls_sha, work, fault="none"):
    require(fault in FAULTS, "UNKNOWN_NEGATIVE_CASE")
    require(not work.exists(), "VERIFICATION_DIRECTORY_EXISTS")
    work.mkdir(parents=True)
    run_id = number(run_id)
    run = api(APP, f"actions/runs/{run_id}")
    source_sha, attempt = validate_run(run, run_id)
    protected_context(source_sha, controls_sha)
    listing = api(APP, f"actions/runs/{run_id}/artifacts?per_page=100")
    require(listing["total_count"] < 100, "ARTIFACT_PAGINATION_REQUIRED")
    release = select_artifact(listing["artifacts"], artifact_name("release", source_sha, run_id, attempt), run_id, source_sha)
    record_artifact = select_artifact(listing["artifacts"], artifact_name("receipt", source_sha, run_id, attempt), run_id, source_sha)
    file = download(release, "release.zip", work)
    receipt_file = download(record_artifact, "release-record.json", work)
    if fault == "tampered-bytes":
        file.write_bytes(file.read_bytes() + b"synthetic-negative-test")
    if fault == "missing-record":
        receipt_file.unlink()
    require(receipt_file.is_file(), "SIGNED_RECEIPT_REQUIRED")
    verify_signature(file, source_sha, controls_sha, run_id, attempt)
    verify_signature(receipt_file, source_sha, controls_sha, run_id, attempt)
    expected_source = "0" * 40 if fault == "wrong-source" else source_sha
    expected_attempt = attempt + 1 if fault == "wrong-attempt" else attempt
    receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
    validate_receipt(receipt, file, expected_source, release["id"], run_id, expected_attempt)
    # Recheck live main immediately before the ONLY synthetic deployment operation.
    require(api(APP, "git/ref/heads/main")["object"]["sha"] == source_sha, "MAIN_MOVED_BEFORE_DEPLOY")
    require(digest(file) == receipt["sha256"], "BYTES_CHANGED_BEFORE_DEPLOY")
    deployed = work / "synthetic-deployment"
    deployed.mkdir()
    shutil.copyfile(file, deployed / "release.zip")
    require(digest(deployed / "release.zip") == receipt["sha256"], "DEPLOYED_BYTES_MISMATCH")
    summary = dict(receipt, controls_sha=controls_sha, verifier_run_id=os.environ.get("GITHUB_RUN_ID"),
                   verifier_run_attempt=os.environ.get("GITHUB_RUN_ATTEMPT"),
                   attestation_verified=True, synthetic_deployment=True, real_deployment=False)
    (work / "verification-summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("RELEASE_GATE=PASS; SAME_BYTES=PASS; SYNTHETIC_DEPLOYMENT=PASS; REAL_DEPLOYMENT=NO")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "build", "record", "verify"))
    parser.add_argument("--target", type=Path)
    parser.add_argument("--file", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sha", default=os.environ.get("GITHUB_SHA"))
    parser.add_argument("--controls-sha")
    parser.add_argument("--artifact-id")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT"))
    parser.add_argument("--fault", choices=FAULTS, default="none")
    args = parser.parse_args()
    if args.action == "preflight":
        require(os.environ.get("GITHUB_REPOSITORY") == APP and os.environ.get("GITHUB_REF") == "refs/heads/main", "BUILD_CONTEXT_DENIED")
        require(os.environ.get("GITHUB_EVENT_NAME") in ("workflow_run", "workflow_dispatch"), "BUILD_TRIGGER_DENIED")
        protected_context(args.sha, args.controls_sha)
        print("PROTECTED_APPROVED_SOURCE=PASS")
    elif args.action == "build":
        build(args.target, args.output, args.sha)
    elif args.action == "record":
        record(args.file, args.output, args.sha, args.artifact_id, args.run_id, args.attempt)
    else:
        require(os.environ.get("GITHUB_REPOSITORY") == APP and os.environ.get("GITHUB_REF") == "refs/heads/main", "VERIFIER_CONTEXT_DENIED")
        verify_release(args.run_id, args.controls_sha, args.output, args.fault)


if __name__ == "__main__":
    try:
        main()
    except GateError as error:
        raise SystemExit(f"RELEASE_GATE_FAIL={error}") from None
    except Exception as error:
        raise SystemExit(f"RELEASE_GATE_FAIL=INVALID_OR_UNAVAILABLE_EVIDENCE_{type(error).__name__}") from None
