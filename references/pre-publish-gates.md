# Pre-publish gates

Run only checks configured for the project, and report absent checks as
`NOT_CONFIGURED` or `NOT_APPLICABLE`, never as `PASS`.

## Security, privacy, and provenance

Scan worktree, index, every ref, merge, tag, deleted blob, and build artifact
for API keys, PATs, access/refresh tokens, passwords, cookies, sessions, SSH
private keys, cloud/database/SMTP credentials, certificates, and `.env*`.
Also inspect phone numbers, private email lists, addresses, identities,
browser profiles, unredacted logs, user data, and real collection exports.

Review provenance and redistribution rights for direct/transitive dependencies,
vendored code, images, logos, fonts, audio, video, models, datasets, and
templates. Unknown or conflicting license evidence is a hard stop.

Prefer a pinned Gitleaks/TruffleHog-equivalent scanner. If unavailable, use
`scan_sensitive_content.py` as a conservative fallback and label its limited
coverage; a fallback is not an equivalent guarantee. Never print a finding.
Push Protection is fail-closed: remove/rotate the secret, clean affected
history with separate authorization when needed, and rescan. Never bypass.

## Workflow permission gate

After building the exact manifest, run workflow-scope-preflight.md when it
contains .github/workflows/**. Bind the result to the final push protocol and
credential source. A missing, mismatched, or unverified applicable permission
sets READY_TO_PUBLISH = NO before repository creation or push.

## Quality gates

Evaluate `TESTS`, `COVERAGE`, `LINT`, `TYPECHECK`, `BUILD`, `FORMAT`,
`DEPENDENCY_AUDIT`, `YAML_VALIDATION`, `UTF8_TEXT_GATE`, `MARKDOWN_LINKS`,
`README_IMAGES`, and `BUILD_ARTIFACT_CONTENT`. Preserve configured coverage
thresholds; do not exclude stable source to inflate a percentage.
