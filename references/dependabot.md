# Dependabot

`DEPENDABOT_REVIEW` is read-only: do not comment, close, approve, merge, or
alter a PR. Inspect the version span, release notes, changed files, dependency
graph, lockfile, compatibility, security advisories, and isolated test/build
results. State missing tests or release evidence as `NOT_VERIFIED`.

`DEPENDABOT_MERGE` requires `APPROVE_GITHUB_PR_MERGE`, a list of exact PR
numbers, and the Pull Request merge gates. Determine order from dependency
relationships and file conflicts; after each merge, refresh main, live heads,
checks, and remaining named PRs. Generate a local report. Do not process a new
or unnamed PR that appears during the task, and do not use admin merge or
force-push.
