# Local reports and resume

These reports are `LOCAL_ONLY`:

`PRE-PUBLISH-REPORT.md`, `POST-PUBLISH-REPORT.md`, `UPDATE-REPORT.md`, and
`DEPENDABOT-REPORT.md`. Keep them ignored, untracked, unstaged, outside the
public manifest, commit, and push. An ignored report still exists and must be
checked directly for readability and completeness.

Resume state belongs at `.local-audit/github-oss-release-state.json` and must
be ignored, non-public, and free of token values, secrets, full private email,
and raw credentials. Required fields:

```text
SKILL_VERSION, TASK_TYPE, PROJECT_ROOT_FINGERPRINT, PROJECT_HEAD,
REMOTE_URL, EXPECTED_OWNER, FILE_HASHES, COMPLETED_PHASES,
VALIDATION_RESULTS, AUTHORIZATION_SCOPE, BLOCK_REASON, NEXT_SAFE_STEP,
CREATED_AT, UPDATED_AT
```

On resume compare project HEAD and relevant file hashes, invalidate only gates
whose inputs changed, retain unchanged evidence with its source/time, and run a
fresh final integrity check. Never resume a write after owner, repository,
branch, approval scope, or target state changes.
