import importlib.util
from pathlib import Path
import pytest

spec = importlib.util.spec_from_file_location("evidence", Path(__file__).resolve().parents[1] / "scripts/evidence.py")
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


def test_absence_is_unknown():
    assert set(evidence.coverage({}).values()) == {"UNKNOWN"}


def test_statuses():
    result = evidence.coverage({"ownership": False, "repository_identity": True, "release_branches": "NOT_APPLICABLE"})
    assert result["ownership"] == "FAIL"
    assert result["repository_identity"] == "PASS"
    assert result["release_branches"] == "NOT_APPLICABLE"


@pytest.fixture
def chain():
    return dict(application_id="APP-00427", repository_id="10001", commit_sha="a" * 40,
                build_id="build-demo-1", artifact_digest="sha256:" + "b" * 64,
                deployment_id="deploy-demo-1", cloud_resource_id="arn:aws:ecs:us-east-1:000000000000:service/synthetic/sample-api",
                runtime_digest="sha256:" + "b" * 64)


def test_matching_chain(chain):
    result = evidence.correlate(chain, chain)
    assert result["result"] == "PASS"
    assert result["verified_deployment_provenance"] is False


@pytest.mark.parametrize("field", ["repository_id", "commit_sha", "artifact_digest"])
def test_mismatch(chain, field):
    changed = dict(chain)
    changed[field] = "mismatch"
    assert evidence.correlate(chain, changed)["result"] == "FAIL"


def test_tag_without_evidence(chain):
    assert evidence.correlate(chain, {"application_id": "APP-00427"})["result"] == "UNKNOWN"
