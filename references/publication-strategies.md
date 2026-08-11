# Publication strategies

Choose from evidence, not convenience. Preserve the old workspace and never
silently rewrite history.

## `PRESERVE_EXISTING_HISTORY`

Use only when every reviewed commit/ref is safe, the worktree is owned and
clean enough, secrets and unlicensed assets are absent, and the approved
history is suitable for public release.

## `CLEAN_WORKTREE_FROM_SAFE_HISTORY`

Use when history is safe but the current worktree contains unfinished or
unrelated changes. Isolate the approved snapshot with a safe branch, temporary
worktree, or equivalent non-destructive copy. Do not reset, clean, or delete
unknown files.

## `FRESH_CLEAN_PUBLIC_HISTORY`

Use only when history contains or may contain secrets, privacy, unlicensed
assets, unsuitable large files, or cannot be reliably verified. Keep the old
workspace intact; create an independent public directory without its `.git`,
then make one new clean first commit from the approved snapshot. This requires
`APPROVE_GIT_HISTORY_REMEDIATION` when history is changed or excluded.

## `CONTINUE_EXISTING_REMOTE`

Use for an existing non-empty target. Fetch/clone only with read-only evidence,
compare histories, and integrate through a normal branch/PR or non-destructive
fast-forward. Never overwrite the target with force-push.
