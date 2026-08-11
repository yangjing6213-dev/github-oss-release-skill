# Project updates

Read local rules and remote state, classify each dirty path, then test the
approved change. Use exactly one classification:

| Class | Meaning | Action |
|---|---|---|
| `CURRENT_TASK_CHANGE` | owned by this request | may be staged explicitly |
| `PREEXISTING_UNRELATED_CHANGE` | user work outside this request | preserve and exclude |
| `MIXED_CHANGE` | one path contains both | stop and ask for separation |
| `UNKNOWN_CHANGE` | ownership cannot be proven | stop |

Never use `git reset --hard`, `git clean`, an untracked stash, or deletion to
make a worktree look clean. Choose `PROJECT_UPDATE` for an allowed direct
update; choose `BRANCH_AND_PR_UPDATE` when the main branch is protected, a PR is
required, or isolation is safer. Use an explicit manifest, commit only owned
files, and re-read remote HEAD after ordinary push/PR creation.

## Checkpoint reuse

For a single docs/link change, invalidate `MARKDOWN_LINK_GATE`,
`README_LINK_GATE`, and `FINAL_INTEGRITY_GATE`; rerun those gates and the final
complete check. Reuse `HISTORY_SCAN`, `LICENSE_AUDIT`, and `DEPENDENCY_AUDIT`
only when their inputs and evidence hashes are unchanged. Any source, lockfile,
build, dependency, secret, or history change invalidates its related evidence.
Never treat a stale pass as current merely because the change is small.
