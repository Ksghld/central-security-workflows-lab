# Secure Code Controls Lab

This central repository contains synthetic security policy, application ownership
validation, offline inventory evaluation, and code-to-cloud correlation exercises.
It uses GitHub-hosted ubuntu-latest jobs only. It never builds or deploys an
application and never executes application-controlled scripts or dependencies.

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

Publication uses the established controlled GitOps process after audit approval.
Repository creation, installation scope, and Rulesets are administrator actions.
The execution agent uses approved feature worktrees and human-reviewed draft PRs.
