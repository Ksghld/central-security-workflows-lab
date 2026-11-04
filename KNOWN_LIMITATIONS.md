# Known Limitations

This is a local synthetic lab, not production security enforcement.
No remote publication, Ruleset, denial, human review, or workflow run is verified.

- Only src and optional infra text files are scanned for four harmless markers.
  Required target/configuration errors, oversized inputs, and symlinks fail closed.
  This is not a real SCA, SAST, secret detector, or IaC parser.
- Application metadata is untrusted and compared to the central registry.
  The current synthetic repository identity intentionally fails for real repositories.
  Binding the authorized public ID requires a reviewed central change and new immutable pins.
- Inventory evaluates normalized offline evidence, not raw GitHub API responses.
  Missing evidence is UNKNOWN. It does not query organization-wide inventory.
- Release correlation compares synthetic records. The actual checkout SHA is separately
  compared to the GitHub event SHA; no artifact is built, signed, deployed, or attested.
- Immutable central checkout protects scanner content from application changes, but an
  application contributor can replace the caller with a same-named passing job.
  The offline negative test illustrates this, not a remotely demonstrated bypass.
- GitHub Actions as Expected Source does not establish workflow integrity.
  Production requires an independently controlled security check publisher or a mandatory
  trusted workflow enforcement mechanism appropriate to the platform/plan.
- CODEOWNERS requires real authorized reviewers with repository access. None are invented.
  Administrator onboarding must establish CODEOWNERS for workflows, policies, scanners,
  and CODEOWNERS itself, protected main and separate central review. These are not applied.
- No four-eyes enforcement claim without two independent identities actually participating.
- Heuristic privacy scanning cannot guarantee detection of every possible secret.
- Hosted workflow execution and third-party Action runtime compatibility remain untested.
  Immutable pins were matched to official upstream releases, not exhaustively audited.

