# Pull requests

## Read-only review

Record these fields for the specific PR:

`PR_AUTHOR`, `PR_STATE`, `IS_DRAFT`, `BASE_BRANCH`, `BASE_SHA`, `HEAD_SHA`,
`CHANGED_FILES`, `MERGEABLE`, `CHECKS`, `CI`, `CODEQL`, and
`BREAKING_CHANGES`. Use the live `HEAD_SHA`; do not infer mergeability from a
stale page or an unverified draft.

## Merge

Require the exact `APPROVE_GITHUB_PR_MERGE` and named PR number. Revalidate
author, state, base/head, changed files, checks, CI, CodeQL, conflicts, and
authorization immediately before merge. If the head changes, restart the
review. Merge overlapping PRs in dependency/file-conflict order and recheck the
remaining named PRs after every merge. Never use `--admin`, merge an unnamed PR,
or force-push.
