# Central validation architecture

The caller passes scan_mode, application_id and policy_profile. It does not pass
scanner code or an arbitrary controls revision. The central workflow checks out
the target into target/ and a fixed controls commit into controls/. Python isolated
mode runs controls/scripts/validate.py. No target scripts, hooks, package installs,
builds, or privileged tokens are used.

Metadata records repository identity, source/target branch, PR head SHA, validation
SHA and checked-out tested SHA. A PR's validation SHA is normally its synthetic
test-merge revision. A release push must be verified against actual main SHA.

Monitoring reports findings after a push is accepted. Enforcement fails on blocking
findings, bad ownership, missing/invalid policy or incomplete scans. Runtime errors
produce tool_error and nonzero exit. Artifact upload failure is also visible.

Inventory evaluates supplied offline evidence; it cannot establish live GitHub
coverage without authentic, current inputs. Correlation compares synthetic identity,
SHA, build, digest, deployment and runtime records. Matching values are metadata
correlation, not signed deployment provenance.

A same-named replacement caller can bypass central execution. Required GitHub
Actions checks alone do not authenticate workflow contents. Production needs a
mandatory trusted control or independent security-owned check publisher, central
review, and restricted bypass. No such independent enforcement is claimed here.
