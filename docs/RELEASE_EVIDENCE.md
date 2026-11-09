# Release evidence extension: prepared, not remotely demonstrated

This extension is separate from the P0 PR Security Gate. It packages only
synthetic text; it does not build or deploy a real application. The artifact
bytes, GitHub run IDs, artifact IDs, and attestations will be real when the
reviewed workflows run in GitHub. Unit fixtures are synthetic, not proof.

## Trust boundaries

- `release-build.yml` is a centrally reviewed, immutable reusable builder.
  It requires exact current application `main`, independent approval of its
  merged PR, exact-SHA post-merge validation, and active main-only CODEOWNERS
  rulesets in both repositories. It packages `src/*.txt` as data, never runs
  application commands, and uses no application dependencies or caches.
- The builder uploads `release.zip`, records its actual SHA-256 and returned
  Artifact ID together with the source SHA, run ID and attempt, then attests
  both file and receipt using GitHub OIDC. No stored signing key is used.
- `release-verify.yml` runs on a new GitHub-hosted runner with read-only token
  permissions and no OIDC signing permission. It retrieves the exact build's
  artifacts and invokes `gh attestation verify` with pinned signer workflow,
  signer commit, source commit, main ref, and GitHub-hosted runner requirement.
- It checks the verified certificate's invocation URI for the exact run and
  attempt. A self-reported JSON predicate alone is insufficient. It verifies
  the signed receipt, rechecks current main, copies only those verified bytes
  to a local `synthetic-deployment/` directory, and hashes the copy again.
- The verifier is an independent job and trust configuration, not an external
  CD system or an independent organizational authority. GitHub, its hosted
  runner, reviewed central code, and protected application caller are trusted.
  Repository administrators can change those controls. No production or
  cloud-deployment enforcement is claimed.

## Permissions

Builder: contents/actions/pull-requests read, id-token/attestations write.
Verifier: contents/actions/pull-requests/attestations read only. Both are scoped
to these two public lab repositories. API operations in the Python verifier
are GET only. Artifact upload and attestation creation are the intended writes.
Artifacts expire after seven days; expired or missing evidence fails closed.
Public attestations can outlive artifacts and disclose normal public GitHub
repository/workflow/commit metadata. Do not add private payloads or identities.

## Controlled publication and activation

1. Merge reviewed CODEOWNERS changes in both repos; enable required code-owner
   approval. Protect central main with no bypass, PRs, one independent review,
   stale dismissal, latest-push approval, no deletion/force push.
2. Observe `central-controls-tests` from GitHub Actions on a real PR before
   requiring that exact check with strict freshness. Do not invent a check.
3. Review and merge central release changes with a merge commit (not squash or
   rebase), retaining the immutable implementation and signer ancestors.
4. Verify each pinned commit exists remotely and is reachable from central
   main before publishing the application caller PR. Existing P0 scanner pins
   remain unchanged. New release pins are functional additions, not privacy
   history cleanup.
5. Independently review/merge application callers. Main post-merge validation
   triggers the build; successful build triggers the separate verifier.
   Fail closed until both rulesets and evidence are available.

## Required live acceptance evidence (not yet collected)

Record source SHA, build run ID/attempt, release Artifact ID, actual release
SHA-256, attestation URL, verifier run URL and summary. Demonstrate one passing
same-bytes synthetic deployment. Then manually run the verifier against the
same build with `tampered-bytes`, `missing-record`, `wrong-source`, and
`wrong-attempt`. Each must fail and produce no synthetic-deployment success.
These negative choices only corrupt local test inputs or expected identities;
none relaxes signature verification or allows an alternate signer.

PR merge enforcement and post-merge release enforcement are different gates.
A green PR check does not prove release provenance, and a failed release gate
cannot undo a merge. Cortex scans, authoritative CMDB, external CD and runtime
code-to-cloud reconciliation remain future work.

References: [GitHub artifact attestations](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations),
[GitHub CLI verification](https://cli.github.com/manual/gh_attestation_verify).

Local validation snapshot, 2026-11-09: 87 central tests passed, including workflow
permissions/pins, signed-receipt correlation, missing evidence, tampering, exact
run attempt and main-movement rejection. Python compilation passed. Fixtures mock
GitHub and cryptographic command outcomes; they do not verify a live signature.
