# Repository standard

## Purpose and layout

This repository publishes the `github-oss-release` Codex Skill as a standalone
community project. The Skill entry point is `SKILL.md`; its runtime support is
organized as follows:

```text
agents/       Codex interface metadata
references/   workflow, safety, policy, and report contracts
scripts/      read-only discovery, validation, scanning, and manifest helpers
templates/    local-only report templates
tests/        synthetic scenarios and standard-library smoke tests
.github/      CI, Dependabot, issue forms, and PR template
```

Do not copy installed-runtime `.git` data, local reports, caches, private
fixtures, or generated artifacts into a public snapshot.

## Runtime and dependencies

- Python 3.10 or newer is required by the script syntax.
- There is no package manager, package manifest, or lockfile in this repository.
- The validators use the Python standard library. `validate_skill.py` can use
  an installed PyYAML parser; without it, it uses a conservative basic YAML
  check. PyYAML is not vendored or redistributed here.

## Canonical checks

Run from the repository root:

```powershell
python scripts/validate_skill.py .
python scripts/run_scenario_tests.py
python scripts/validate_chinese_result_policy.py
python tests/test-scripts.py
python scripts/validate_utf8.py --root .
python scripts/check_markdown_links.py .
python scripts/scan_sensitive_content.py .
```

`quick_validate.py` is not part of this repository's validation contract; the
listed validators are the canonical checks. Coverage, build, and build-artifact
inspection are not applicable because this directory-based Skill has no
coverage threshold, package build, or release artifact. Dependency audit is not
applicable because the published Python scripts have no external runtime
dependencies. Lint, typecheck, and format remain
`NOT_CONFIGURED_NON_BLOCKING`; Python syntax, tests, and Skill validation must
still pass.

## Branching and versioning

Use a focused branch for review-sensitive work. Keep `main` releasable and use
normal fast-forward or PR integration. The Skill version is recorded in
`SKILL.md` and related policy files; update the changelog only with verified
facts. Never rewrite public history or force-push.

## Licensing and provenance

The repository is distributed under the [MIT License](../LICENSE), Copyright
(c) 2026 ENHE AI Studio. Contributors must prove that added code,
documentation, fixtures, templates, fonts, images, and other assets may be
redistributed under compatible terms. Do not add copied material with unknown
or conflicting licenses. Optional dependencies remain the responsibility of
the environment that installs them.

## Disclosure and platform safety

Use the private process in `SECURITY.md` for vulnerabilities. Keep reports,
credentials, and user data out of commits. The release Skill defaults to
read-only and requires exact, task-specific authorization before GitHub writes.
Observe GitHub policy and stop on account restrictions, Push Protection, or
unknown target state.

## CI and release gates

CI has read-only repository permissions and runs the configured validators and
stdlib tests. CI success is local/remote check evidence, not permission to
publish. A release requires a complete ignored pre-publish report, an exact
public manifest, final drift checks, and the authorization named in `SKILL.md`.
