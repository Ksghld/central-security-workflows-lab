# Repository-scoped governance

The proposed JSON is a review artifact, NOT applied configuration. It targets only
refs/heads/main. Feature branches remain unrestricted for ordinary development;
PR rules govern the target/base branch, not every source branch.

Human owner: @kfise (admin permission verified in both public lab repositories).
Use public handles, not email addresses, in CODEOWNERS. The files cover caller and
central workflows, identities, policies, scanner code and CODEOWNERS itself.

## Apply only to the two public lab repositories

Application: edit existing Ruleset-branch-test (26795523), do not create a competing
ruleset. Keep Active, target main, empty bypass list, PR with one approval, stale
review dismissal, latest reviewable push approval, resolved threads, strict branch
freshness, no force push and no deletion. Enable required CODEOWNER review.
Retain the observed GitHub Actions check appsec-pr-gate / security-validation
(integration 15368). The proposed JSON records exactly these settings.

Central: create central-main-review from its proposed JSON, with the same main-only
PR/review/force-push/deletion protections. There is currently no central-native
required check. Do NOT select an invented check. The proposed Central Controls Tests
workflow must first run on the governance PR; inspect its actual check name, source
and SHA. Only after a successful observed run add that check with strict freshness.
The expected YAML job name is central-controls-tests, but observation is authoritative.
No organization rules, GitHub App permissions, other repositories or runtime are changed.

## Verify after human application and merge

1. Read back enforcement=active, main-only condition, required check/source and no bypass.
2. Merge the CODEOWNERS changes only after independent review. Their first PR cannot
   auto-request owners from a CODEOWNERS file that is not yet on its base branch.
3. Open a new harmless MJ PR changing an owned path; verify requested_reviewers
   includes kfise and no CODEOWNERS API syntax errors. An explicit bootstrap review
   request is useful, but is NOT evidence of automatic CODEOWNERS review.
4. Confirm no approval means blocked; one independent owner approval satisfies review.
5. Push a further harmless reviewable change; record old review DISMISSED, fresh head
   SHA/checks, and another approval required. Leave merge to the human.
6. Record exact resulting main SHA and post-merge verification where the workflow exists.

CODEOWNERS is review ownership, not a security scanner. Expected-source GitHub Actions
checks alone cannot guarantee the caller invoked central controls. Independent trusted
invocation and CD admission remain future architecture.

Sources: [GitHub CODEOWNERS](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners),
[GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets).
