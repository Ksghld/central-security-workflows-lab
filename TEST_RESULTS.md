# Test Results

Date: 2026-11-03. LOCAL ONLY.

Combined pytest: 48 passed, 0 failed (application 13; central 35).
The original eight P0 scanner tests remain; four workflow contracts were migrated.
Two additional cross-revision tests compare the caller's pinned workflow and the
central checkout's scanner/policy files byte-for-byte with the tested local files.
Central coverage includes ownership/identity, four marker families, monitor/enforce,
missing/malformed policy and incomplete scan failure, offline inventory with absent
evidence and stale attempts, synthetic correlation mismatches, and actual checkout SHA checks.
The local workflow-tampering example does not demonstrate GitHub merge enforcement.

Executed offline inventory command:
```text
python scripts/evidence.py fixtures/inventory.json reports --registry policies/default.json
```
Run from central checkout. Generated coverage.json, coverage.md and coverage.csv.
These fixtures deliberately omit remote rules and runs; those controls report UNKNOWN.
Reports are ignored, not evidence of actual GitHub settings.

YAML/contract checks passed; the GitHub workflow service has NOT executed these files.
Official upstream releases confirm checkout v4.2.2 at 11bd71901bbe5b1630ceea73d27597364c9af683
and upload-artifact v4.6.2 at ea165f8d65b6e75b540449e92b4886f43607fa02.
Local git ls-remote failed due to network resolution; public upstream pages provided verification.

NOT_EXECUTED: remote publication, hosted Actions, real check discovery, Rulesets,
denied merge/direct push, fresh PR enforcement, post-merge verification, remote
ownership/digest failures, independent review, and remote workflow-tamper demonstration.

