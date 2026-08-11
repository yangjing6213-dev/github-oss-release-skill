# Repository discovery

Collect these fields before selecting a publication strategy:

```text
PROJECT_ROOT
PROJECT_NAME
PROJECT_NAME_ZH
PROJECT_NAME_EN
PROJECT_TYPE
PROJECT_PURPOSE
PROJECT_VERSION
TECH_STACK
PACKAGE_MANAGER
ENTRY_POINTS
BUILD_COMMANDS
TEST_COMMANDS
COVERAGE_COMMANDS
LINT_COMMANDS
TYPECHECK_COMMANDS
FORMAT_COMMANDS
DEPENDENCY_AUDIT_COMMANDS
CURRENT_BRANCH
CURRENT_HEAD
CURRENT_REMOTE
CURRENT_WORKTREE
CURRENT_HISTORY
EXISTING_GITHUB_FILES
```

Use project metadata first, then the README, then the directory name for the
project name. Prefer configured commands and lockfiles over guesses. Inspect
status, branch, HEAD, remotes, tracked/ignored files, nested repositories,
large files, symlinks, and generated artifacts without changing them. Redact
remote credentials and private addresses.

If the root, project purpose, repository name, or target cannot be reliably
identified, stop and ask one focused question. Never invent a package manager,
test pass, version, owner, or repository URL.
