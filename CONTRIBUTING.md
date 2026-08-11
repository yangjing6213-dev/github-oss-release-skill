# Contributing

Thank you for helping improve `github-oss-release`.

## Before opening a change

- Use a focused branch and keep unrelated work out of the change.
- Do not include tokens, private email, private paths, user data, logs, or real project fixtures.
- Use generic placeholders such as `<owner>/<repository>` and synthetic fixtures.
- Preserve the fail-closed authorization, secret, license, account, and platform gates.
- Report vulnerabilities privately as described in [SECURITY.md](SECURITY.md).

## Local checks

Run the checks that match your change; changes to policy or scripts should run
the complete set:

```powershell
python scripts/validate_skill.py .
python scripts/run_scenario_tests.py
python scripts/validate_chinese_result_policy.py
python tests/test-scripts.py
python scripts/validate_utf8.py --root .
python scripts/check_markdown_links.py .
python scripts/scan_sensitive_content.py .
```

The fallback secret scan does not replace a history-aware scanner before
publication. Run `inspect_build_artifacts.py` only when build artifacts are
present; otherwise record `NOT_CONFIGURED`.

## Pull requests

Describe the problem, the smallest solution, affected safety rules, tests, and
documentation. Keep commands and bilingual facts synchronized. Reviewers may
request provenance or license evidence for copied code, fixtures, templates,
or assets. Contributions accepted by this project are distributed under the
[MIT License](LICENSE); contributors must have the rights needed to submit
their work under those terms.

Use clear commit messages and do not force-push shared review branches without
maintainer coordination. Do not submit material with unknown, conflicting, or
unmet attribution requirements.
