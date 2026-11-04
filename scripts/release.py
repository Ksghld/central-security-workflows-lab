"""Fail-closed synthetic release correlation; never deploys or executes target code."""
import argparse
import importlib.util
import json
from pathlib import Path


def verify(target, expected_path, tested_sha, validation_sha):
    if not tested_sha or tested_sha != validation_sha:
        raise ValueError("checkout does not match event SHA")
    observed_path = target / "release-evidence.json"
    if observed_path.is_symlink() or not observed_path.is_file():
        raise ValueError("missing release evidence")
    spec = importlib.util.spec_from_file_location("central_evidence", Path(__file__).with_name("evidence.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    observed = json.loads(observed_path.read_text(encoding="utf-8"))
    result = module.correlate(expected, observed)
    result.update(tested_sha=tested_sha, github_validation_sha=validation_sha,
                  note="Fixture commit is synthetic; event SHA separately verifies the checkout.")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--expected", type=Path, required=True)
    parser.add_argument("--tested-sha", required=True)
    parser.add_argument("--validation-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.target, args.expected, args.tested_sha, args.validation_sha)
        code = 0 if result["result"] == "PASS" else 2
    except Exception as error:
        result = {"result": "tool_error", "synthetic": True, "error_type": type(error).__name__}
        code = 3
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
