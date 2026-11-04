"""Central synthetic validator. Target files are data, never executable code."""
import argparse
import json
import os
from pathlib import Path

MARKERS = {"sca": "SIMULATED_CRITICAL_SCA", "sast": "SIMULATED_CRITICAL_SAST",
           "secrets": "SIMULATED_CRITICAL_SECRET", "iac": "SIMULATED_CRITICAL_IAC"}


def read_data(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("missing or unsafe input")
    return json.loads(path.read_text(encoding="utf-8"))


def validate(root, policy, application_id, repository, repository_id, mode):
    if mode not in ("monitor", "enforce"):
        raise ValueError("invalid mode")
    if set(policy["required_engines"]) != set(MARKERS) or not policy["version"]:
        raise ValueError("incomplete policy")
    approved = policy["applications"][application_id]
    declared = read_data(root / "application.json")
    expected = dict(approved, application_id=application_id)
    if declared != expected or approved["repository"] != repository or approved["repository_id"] != repository_id:
        raise ValueError("invalid ownership or repository identity")
    source = root / "src"
    if source.is_symlink() or not source.is_dir():
        raise ValueError("required scan target missing")
    findings = []
    files = 0
    targets = list(source.rglob("*"))
    infrastructure = root / "infra"
    if infrastructure.is_symlink():
        raise ValueError("symlink target rejected")
    if infrastructure.exists():
        targets.extend(infrastructure.rglob("*"))
    if len(targets) > 10000:
        raise ValueError("scan limit exceeded")
    total_bytes = 0
    for path in targets:
        if path.is_symlink():
            raise ValueError("symlink target rejected")
        if not path.is_file():
            continue
        if path.stat().st_size > 1000000:
            raise ValueError("scan limit exceeded")
        total_bytes += path.stat().st_size
        if total_bytes > 10000000:
            raise ValueError("scan limit exceeded")
        text = path.read_text(encoding="utf-8")
        files += 1
        for engine, marker in MARKERS.items():
            if marker in text:
                findings.append({"engine": engine, "severity": "critical", "path": path.relative_to(root).as_posix()})
    if not files:
        raise ValueError("incomplete scan")
    return {"simulated": True, "policy_version": policy["version"], "scan_mode": mode,
            "repository": repository, "repository_id": repository_id,
            "application_id": application_id, "executed_engines": sorted(MARKERS),
            "findings": findings, "result": "blocked" if findings and mode == "enforce" else "observed" if findings else "clean"}


def main():
    parser = argparse.ArgumentParser()
    for name in ("target", "policy", "application-id", "repository", "repository-id", "mode", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args()
    try:
        result = validate(Path(args.target), read_data(Path(args.policy)), args.application_id,
                          args.repository, args.repository_id, args.mode)
        code = 2 if result["result"] == "blocked" else 0
    except Exception as error:
        result = {"simulated": True, "result": "tool_error", "error_type": type(error).__name__}
        code = 3
    result.update({
        "repository": os.environ.get("GITHUB_REPOSITORY", args.repository),
        "repository_id": os.environ.get("GITHUB_REPOSITORY_ID", args.repository_id),
        "source_branch": os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME", ""),
        "target_branch": os.environ.get("GITHUB_BASE_REF", ""),
        "pr_head_sha": os.environ.get("PR_HEAD_SHA", ""),
        "github_validation_sha": os.environ.get("GITHUB_SHA", ""),
        "tested_sha": os.environ.get("APPSEC_TESTED_SHA", ""),
        "event": os.environ.get("GITHUB_EVENT_NAME", "local"),
        "scan_mode": args.mode,
    })
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
