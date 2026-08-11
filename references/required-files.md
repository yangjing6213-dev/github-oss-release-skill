# Required repository files

Use this contract when creating or reviewing release files. Adapt examples to the detected stack and verified project facts; never invent commands, guarantees, maintainers, versions, badges or support channels.

## Documentation and governance

- `README.md`: Simplified Chinese overview, problem, features, requirements, install/run, usage, configuration, tests, security boundary, license, contribution link, support link and English document link.
- `README.en.md`: faithful English counterpart with a Chinese document link. Keep code, commands, URLs and facts synchronized. Preserve a documented existing naming convention when upgrading an established project.
- `LICENSE`: exact SPDX-recognized license selected by the owner. Preserve required copyright and third-party notices. Missing or ambiguous licensing blocks publication.
- `CONTRIBUTING.md`: code of conduct, setup, branch/commit/PR expectations, tests, review, security-reporting boundary and license/attribution rules.
- `SECURITY.md`: supported versions, private vulnerability-reporting channel, response expectations and “do not disclose publicly before coordination”. Do not publish a secret contact address unless verified.
- `SUPPORT.md`: supported scope, questions/how-to path, bug path, unsupported requests and response expectations. Do not promise an SLA without evidence.
- `CODE_OF_CONDUCT.md`: an approved code of conduct with attribution/version where required.
- `CHANGELOG.md`: Keep-a-Changelog-style unreleased section plus only verified historical entries; do not fabricate release history.
- `AGENTS.md`: repository-specific commands, directory ownership, secret handling, test requirements, review rules and the publish safety boundary.
- `docs/REPOSITORY_STANDARD.md`: actual layout, supported runtimes, package manager/lockfile, canonical checks, branching/versioning, licensing, disclosure, CI and release gates.

## GitHub configuration

- `.gitignore`: ignore secrets, local environments, caches, dependency folders, build output, editor/OS files and generated artifacts while preserving required fixtures.
- `.env.example`: variable names, type/format comments, safe placeholders such as `replace-me`, and a warning never to commit real values. It must not be copied from `.env`.
- `.github/ISSUE_TEMPLATE/bug_report.yml`: reproducible description, environment, logs with secret-redaction warning, expected/actual behavior and checklist.
- `.github/ISSUE_TEMPLATE/feature_request.yml`: problem, proposed behavior, alternatives, scope and willingness to contribute.
- `.github/pull_request_template.md`: summary, linked issue, tests, docs, compatibility/migration, security and license checklist.
- `.github/workflows/ci.yml`: least-privilege permissions, pinned or controlled actions, lockfile-aware setup, project-specific test/lint/build, cancellation, and no secret values in logs. Do not add deployment or publishing jobs unless separately approved.
- `.github/dependabot.yml`: only ecosystems/directories that exist; bounded update cadence and grouped updates where appropriate. Do not enable unsupported registries or leak credentials.

## Visual assets

Apply `VISUAL_ASSET_POLICY = OPTIONAL_BY_PROJECT` from [visual-assets-publication.md](visual-assets-publication.md). Do not require a Logo, Cover, Screenshot or Demo merely to complete a checklist. When a project does not need visual assets, verify that README files have no broken or misleading image references and record `NOT_REQUIRED_FOR_CURRENT_RELEASE`. When visual assets are included, require documented provenance, redistribution rights, truthful content, privacy review and successful decoding/rendering checks.

## Acceptance checks

Check UTF-8/line endings as appropriate, links and paths, active image references, YAML validity, Markdown rendering, duplicate/conflicting policy text, and that every documented command exists. Verify CI in the repository's actual runtime; a syntactically valid workflow is not proof that it passes.
