import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release", ROOT / "scripts/release.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.fixture
def target(tmp_path):
    (tmp_path / "release-evidence.json").write_bytes((ROOT / "fixtures/release.json").read_bytes())
    return tmp_path


def test_clean_release(target):
    result = release.verify(target, ROOT / "fixtures/release.json", "c" * 40, "c" * 40)
    assert result["result"] == "PASS"
    assert result["verified_deployment_provenance"] is False


def test_changed_digest(target):
    path = target / "release-evidence.json"
    data = json.loads(path.read_text())
    data["artifact_digest"] = "sha256:" + "d" * 64
    path.write_text(json.dumps(data))
    assert release.verify(target, ROOT / "fixtures/release.json", "c" * 40, "c" * 40)["result"] == "FAIL"


def test_wrong_checkout_sha(target):
    with pytest.raises(ValueError):
        release.verify(target, ROOT / "fixtures/release.json", "c" * 40, "d" * 40)


def test_missing_release_evidence(tmp_path):
    with pytest.raises(ValueError):
        release.verify(tmp_path, ROOT / "fixtures/release.json", "c" * 40, "c" * 40)
