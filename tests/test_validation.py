import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts/validate.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


@pytest.fixture
def sample(tmp_path):
    policy = json.loads((ROOT / "policies/default.json").read_text())
    app = dict(policy["applications"]["APP-00427"], application_id="APP-00427")
    (tmp_path / "application.json").write_text(json.dumps(app))
    (tmp_path / "src").mkdir()
    (tmp_path / "src/demo.txt").write_text("clean")
    return tmp_path, policy, app


def run(sample, mode="enforce", application_id="APP-00427", repository="synthetic/secure-code-controls-lab"):
    root, policy, _ = sample
    return validator.validate(root, policy, application_id, repository, "10001", mode)


def test_clean(sample):
    assert run(sample)["result"] == "clean"


@pytest.mark.parametrize("engine", list(validator.MARKERS))
def test_findings(sample, engine):
    (sample[0] / "src/demo.txt").write_text(validator.MARKERS[engine])
    assert run(sample)["result"] == "blocked"
    assert run(sample, "monitor")["result"] == "observed"


def test_unknown_app(sample):
    with pytest.raises(KeyError):
        run(sample, application_id="UNKNOWN")


def test_unknown_repository(sample):
    with pytest.raises(ValueError):
        run(sample, repository="synthetic/unknown")


@pytest.mark.parametrize("owner", [None, "unapproved-team"])
def test_owner(sample, owner):
    root, _, app = sample
    if owner is None:
        del app["technical_owner"]
    else:
        app["technical_owner"] = owner
    (root / "application.json").write_text(json.dumps(app))
    with pytest.raises(ValueError):
        run(sample)


def test_incomplete_policy(sample):
    sample[1]["required_engines"] = ["sca"]
    with pytest.raises(ValueError):
        run(sample)


def test_incomplete_target(sample):
    (sample[0] / "src/demo.txt").unlink()
    with pytest.raises(ValueError):
        run(sample)
