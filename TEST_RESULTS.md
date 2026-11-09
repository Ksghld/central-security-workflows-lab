# Local Test Results

2026-11-09: 53 passed (application 15; central 38), including five governance
contract tests added to the original 48. Python compilation and clean local mock
scanner also passed. No hosted result is inferred from these local tests.

Run from the application checkout with the central governance checkout as a sibling:

```text
python -m pytest -q tests ../secure-controls-governance-central/tests
python -m compileall -q scripts tests
python scripts/mock_appsec.py --mode enforce --output reports/local-scan.json
```

The central checkout can run `python -m pytest -q tests` independently with
its pinned test requirements. Its new read-only hosted test workflow is proposed;
only a completed GitHub run can establish its real required-check name/source.
Existing caller/scanner pins and byte-for-byte pin regression checks are unchanged.
See the application remote ledger for actual Actions and review observations.
