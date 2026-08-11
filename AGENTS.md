# Repository instructions for agents

## Scope

This repository contains the `github-oss-release` Codex Skill. Keep changes
small, evidence-led, and limited to the requested task. Do not modify an
installed runtime copy while preparing this public project.

## Safety

- Default to read-only inspection.
- Never expose or commit secrets, private email, private paths, user data, or real private-project fixtures.
- Never use `git add .`, `git add -A`, force-push, history rewriting, or Push Protection bypass.
- Keep local reports and `.local-audit/` ignored and outside any public manifest.
- A GitHub write needs the exact task-specific approval and a complete local report.

## Layout

- `SKILL.md`: entry point and highest-priority rules.
- `references/`: detailed task and policy guidance.
- `scripts/`: dependency-light validators and inspectors.
- `templates/`: local-only report templates.
- `tests/`: synthetic scenarios and stdlib smoke tests.
- `.github/`: repository collaboration and CI configuration.

## Required checks

```powershell
python scripts/validate_skill.py .
python scripts/run_scenario_tests.py
python scripts/validate_chinese_result_policy.py
python tests/test-scripts.py
python scripts/validate_utf8.py --root .
python scripts/check_markdown_links.py .
python scripts/scan_sensitive_content.py .
```

Do not claim a missing, skipped, or subset check passed. Keep README facts and
commands synchronized in both languages. Changes to security or authorization
rules need scenario coverage. Run `inspect_build_artifacts.py` only when a
build artifact exists; otherwise record `NOT_CONFIGURED`.
