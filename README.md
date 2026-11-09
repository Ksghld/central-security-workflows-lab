# Secure Code Controls Lab

This central repository contains synthetic security policy, application ownership
validation, offline inventory evaluation, and code-to-cloud correlation exercises.
It uses GitHub-hosted ubuntu-latest jobs only. The P0 validator does not build or
deploy an application and never executes application-controlled scripts or dependencies.

The reusable workflow is `.github/workflows/security-validation.yml`. Application
callers pin it to an immutable revision; the workflow separately pins the trusted
scanner checkout. A central code change requires updating both pins in order.
See ARCHITECTURE.md and KNOWN_LIMITATIONS.md before interpreting a result.

## Local commands

```bash
python -m pytest -q tests
python scripts/evidence.py fixtures/coverage.json reports
python scripts/evidence.py snapshot.json reports --registry policies/default.json
```

The first coverage fixture contains synthetic observations only. The second form
evaluates sanitized offline repository/workflow/Ruleset/check-run records. Missing
evidence is UNKNOWN. No private organization inventory is collected.

Ownership uses application.json in the target and the centrally approved registry.
The registry is bound to the public lab repository name and immutable GitHub
repository ID; a mismatch fails closed.

This repository is public and its immutable workflow runs from the application
repository. The application's P0_REMOTE_VALIDATION.md records observed evidence.
Publication uses approved feature branches and ready-for-review PRs; approvals and
merges remain human actions. No credentials or unrelated runtime changes are involved.

Central-main governance is proposed in docs/governance/README.md. The new read-only
Central Controls Tests workflow tests proposed central changes on GitHub-hosted
runners, without secrets, deployment or application code execution. Its exact check
must be observed in GitHub before it becomes required. Do not change existing
application workflow or scanner pins as part of this governance-only update.

## Prepared release-evidence extension

The additional `release-build.yml` packages synthetic text as data and attests
the actual file plus its Artifact ID receipt. `release-verify.yml` independently
verifies the pinned signer, source, run/attempt and actual bytes before a local
synthetic copy. It cannot sign, deploy to cloud, or execute application code.
The implementation is under review; release-chain execution has not yet been
demonstrated in GitHub.
See [release evidence](docs/RELEASE_EVIDENCE.md) for trust boundaries and the live
passing/failing acceptance matrix. Existing P0 scanner pins remain unchanged.
