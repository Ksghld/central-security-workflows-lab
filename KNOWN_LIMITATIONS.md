# Known Limitations

This P0 lab demonstrates real GitHub execution with synthetic security data.
It is not a production AppSec platform or an artifact/deployment authorization gate.

- SCA, SAST, Secrets and IaC results come from harmless marker matching, not Cortex
  or another real scanner. Only src/ and optional infra/ text are scanned.
- Application identity/ownership is checked against a static central registry.
  The public repository ID binding is real; service/team records are synthetic.
  There is no authoritative CMDB integration.
- Push monitoring cannot undo an accepted feature push. Rules apply to the PR target
  main, not every source branch. Evaluate-mode observations are not enforcement.
- An exact post-merge checkout/event SHA check is real. Build IDs, artifact digests,
  deployment records and runtime resources remain fixture comparisons, not provenance.
- No artifact is built, signed, deployed or independently admitted by CD here.
- Application callers pin central workflow and scanner commits. New central main
  changes do not silently update those pins. Required GitHub Actions source alone
  does not prove caller integrity; a same-name replacement is a known trust limit.
- CODEOWNERS files in a PR are proposals until merged to the base branch. Required
  code-owner review also needs an active rule. Automatic review request and blocking
  need a subsequent PR to be observed, not inferred from local tests.
- The application ruleset is Active. Code-owner review and central-main protection
  remain pending until the administrator applies and we read back the proposed rules.
- Local test totals are not remote acceptance results. See the dated evidence ledger.

## Future work, not P0 claims

Real Cortex integrations; authoritative CMDB; trusted CI Build ID and Artifact Digest
provenance; an independent CD Release Gate; observed code-to-cloud runtime reconciliation;
and security-controlled mandatory invocation that is independent of mutable callers.
