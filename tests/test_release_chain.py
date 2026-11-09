"""Synthetic unit fixtures: these are NOT evidence of live GitHub enforcement."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import zipfile

import pytest

SPEC = importlib.util.spec_from_file_location("release_chain", Path(__file__).resolve().parents[1] / "scripts/release_chain.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)
SHA = "a" * 40
CONTROLS = "b" * 40
RUN = 123
ATTEMPT = 2


def artifact(name, artifact_id=456):
    return {"id": artifact_id, "name": name, "expired": False, "size_in_bytes": 100,
            "workflow_run": {"id": RUN, "head_sha": SHA}}


def run():
    return {"id": RUN, "repository": {"full_name": gate.APP}, "head_repository": {"id": gate.APP_ID},
            "path": gate.BUILD_PATH, "name": "lab-release-build", "head_branch": "main",
            "event": "workflow_run", "status": "completed", "conclusion": "success", "head_sha": SHA,
            "run_attempt": ATTEMPT}


def verified(file_sha):
    return [{"verificationResult": {"signature": {"certificate": {
        "runInvocationURI": f"https://github.com/{gate.APP}/actions/runs/{RUN}/attempts/{ATTEMPT}",
        "sourceRepositoryDigest": SHA, "sourceRepositoryURI": f"https://github.com/{gate.APP}",
        "runnerEnvironment": "github-hosted"}}, "statement": {
            "predicateType": "https://slsa.dev/provenance/v1", "subject": [{"digest": {"sha256": file_sha}}]}}}]


@pytest.mark.parametrize("value", [None, "main", "A" * 40, "a" * 39, "$(echo bad)"])
def test_sha_validation(value):
    with pytest.raises(gate.GateError, match="INVALID_SOURCE_SHA"):
        gate.sha(value)


@pytest.mark.parametrize("value", [None, 0, -1, "1/x", "1;echo", "01"])
def test_id_validation(value):
    with pytest.raises(gate.GateError, match="INVALID_NUMERIC_ID"):
        gate.number(value)


@pytest.mark.parametrize("field,value", [("conclusion", "failure"), ("status", "in_progress"),
    ("head_branch", "feature/test"), ("event", "pull_request"), ("path", ".github/workflows/other.yml"),
    ("name", "untrusted"), ("id", 124)])
def test_run_must_be_exact_successful_main_build(field, value):
    sample = run()
    sample[field] = value
    with pytest.raises(gate.GateError):
        gate.validate_run(sample, RUN)


def test_valid_run():
    assert gate.validate_run(run(), RUN) == (SHA, ATTEMPT)


@pytest.mark.parametrize("change", ["expired", "large", "wrong-run", "wrong-sha", "duplicate", "missing"])
def test_artifact_fail_closed(change):
    item = artifact("release")
    items = [item]
    if change == "expired":
        item["expired"] = True
    elif change == "large":
        item["size_in_bytes"] = gate.MAX_BYTES + 1
    elif change == "wrong-run":
        item["workflow_run"]["id"] += 1
    elif change == "wrong-sha":
        item["workflow_run"]["head_sha"] = CONTROLS
    elif change == "duplicate":
        items.append(copy.deepcopy(item))
    else:
        items = []
    with pytest.raises(gate.GateError):
        gate.select_artifact(items, "release", RUN, SHA)


@pytest.mark.parametrize("names", [["../release.zip"], ["release.zip", "extra"], ["directory/release.zip"]])
def test_zip_layout_denies_extra_and_traversal(names):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        for name in names:
            archive.writestr(name, b"synthetic")
    with pytest.raises(gate.GateError, match="ARTIFACT_LAYOUT_INVALID"):
        gate.extract_one(data.getvalue(), "release.zip")


def test_verified_certificate_binds_exact_attempt_not_predicate():
    result = verified("c" * 64)
    gate.validate_verified_result(result, "c" * 64, SHA, RUN, ATTEMPT)
    result[0]["verificationResult"]["statement"]["predicate"] = {"run_attempt": ATTEMPT + 1}
    with pytest.raises(gate.GateError, match="CERTIFICATE_BINDING"):
        gate.validate_verified_result(result, "c" * 64, SHA, RUN, ATTEMPT + 1)


def test_crypto_verification_is_mandatory_and_pinned(tmp_path, monkeypatch):
    file = tmp_path / "release.zip"
    file.write_bytes(b"synthetic")
    calls = []
    def command(args, category):
        calls.append((args, category))
        return json.dumps(verified(gate.digest(file))).encode()
    monkeypatch.setattr(gate, "command", command)
    gate.verify_signature(file, SHA, CONTROLS, RUN, ATTEMPT)
    args, category = calls[0]
    assert args[:3] == ["gh", "attestation", "verify"]
    assert args[args.index("--signer-digest") + 1] == CONTROLS
    assert args[args.index("--signer-workflow") + 1] == gate.SIGNER
    assert "--deny-self-hosted-runners" in args
    assert "--custom-trusted-root" not in args
    assert category == "ATTESTATION_VERIFICATION_FAILED"


@pytest.fixture
def live_stub(tmp_path, monkeypatch):
    """API/crypto are deliberately mocked; only tests the local decision logic."""
    release = artifact(gate.artifact_name("release", SHA, RUN, ATTEMPT))
    receipt = artifact(gate.artifact_name("receipt", SHA, RUN, ATTEMPT), 457)
    monkeypatch.setattr(gate, "protected_context", lambda *_: None)
    def api(repo, path):
        assert repo == gate.APP
        if path == f"actions/runs/{RUN}":
            return run()
        if "artifacts?" in path:
            return {"total_count": 2, "artifacts": [release, receipt]}
        assert path == "git/ref/heads/main"
        return {"object": {"sha": SHA}}
    monkeypatch.setattr(gate, "api", api)
    def download(item, filename, work):
        file = work / filename
        if filename == "release.zip":
            file.write_bytes(b"synthetic release bytes")
        else:
            gate.record(work / "release.zip", file, SHA, release["id"], RUN, ATTEMPT)
        return file
    monkeypatch.setattr(gate, "download", download)
    def verify(file, *_):
        if file.name == "release.zip" and file.read_bytes() != b"synthetic release bytes":
            raise gate.GateError("ATTESTATION_VERIFICATION_FAILED")
    monkeypatch.setattr(gate, "verify_signature", verify)
    return tmp_path / "verification"


def test_success_copies_the_same_verified_bytes(live_stub):
    gate.verify_release(RUN, CONTROLS, live_stub)
    assert (live_stub / "synthetic-deployment/release.zip").read_bytes() == b"synthetic release bytes"
    summary = json.loads((live_stub / "verification-summary.json").read_text())
    assert summary["artifact_id"] == 456
    assert summary["run_attempt"] == ATTEMPT
    assert summary["real_deployment"] is False


@pytest.mark.parametrize("fault", gate.FAULTS[1:])
def test_negative_cases_never_deploy(live_stub, fault):
    with pytest.raises(gate.GateError):
        gate.verify_release(RUN, CONTROLS, live_stub, fault)
    assert not (live_stub / "synthetic-deployment").exists()


def test_crypto_unavailable_never_deploys(live_stub, monkeypatch):
    def fail(*_):
        raise gate.GateError("ATTESTATION_VERIFICATION_FAILED")
    monkeypatch.setattr(gate, "verify_signature", fail)
    with pytest.raises(gate.GateError):
        gate.verify_release(RUN, CONTROLS, live_stub)
    assert not (live_stub / "synthetic-deployment").exists()


def test_build_packages_only_data_and_is_deterministic(tmp_path, monkeypatch):
    source = tmp_path / "source"
    (source / "src").mkdir(parents=True)
    (source / "src/demo.txt").write_text("Synthetic application data.")
    monkeypatch.setattr(gate, "command", lambda *_: SHA.encode())
    first, second = tmp_path / "one.zip", tmp_path / "two.zip"
    gate.build(source, first, SHA)
    gate.build(source, second, SHA)
    assert first.read_bytes() == second.read_bytes()
    with zipfile.ZipFile(first) as archive:
        assert set(archive.namelist()) == {"src/demo.txt", "source.json"}
    (source / "src/execute.py").write_text("raise RuntimeError('must not execute')")
    with pytest.raises(gate.GateError, match="SOURCE_FILE_TYPE_DENIED"):
        gate.build(source, tmp_path / "denied.zip", SHA)


def test_governance_requires_codeowners(monkeypatch):
    config = json.loads((Path(__file__).resolve().parents[1] / "docs/governance/main-ruleset.proposed.json").read_text())
    config["rules"].append({"type": "required_status_checks", "parameters": {
        "strict_required_status_checks_policy": True,
        "required_status_checks": [{"context": "central-controls-tests", "integration_id": 15368}]}})
    def api(repo, path):
        return [{"id": 1, "enforcement": "active"}] if "?" in path else config
    monkeypatch.setattr(gate, "api", api)
    gate.governance(gate.CENTRAL, "central-controls-tests")
    next(item for item in config["rules"] if item["type"] == "pull_request")["parameters"]["require_code_owner_review"] = False
    with pytest.raises(gate.GateError, match="ACTIVE_CODEOWNER_RULESET_REQUIRED"):
        gate.governance(gate.CENTRAL, "central-controls-tests")
