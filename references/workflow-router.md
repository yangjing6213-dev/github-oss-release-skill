# Workflow router

Set one `TASK_TYPE` before changing files or contacting GitHub. Use the user's
explicit wording first, then verified local metadata and observed repository
state. `Remote Owner` is evidence, not permission.

## Allowed task types

`DISCOVERY_ONLY` · `PRE_PUBLISH_AUDIT` · `INITIAL_PUBLICATION` ·
`PROJECT_UPDATE` · `BRANCH_AND_PR_UPDATE` · `PR_REVIEW` · `PR_MERGE` ·
`DEPENDABOT_REVIEW` · `DEPENDABOT_MERGE` · `RELEASE_PUBLICATION` ·
`REMOTE_MIGRATION` · `AUTH_DIAGNOSIS` · `AUTH_REMEDIATION` ·
`VISUAL_ASSET_PUBLICATION` · `INCIDENT_RECOVERY`

## Routing rules

1. Honor an explicit task type in the current turn.
2. Otherwise combine project state, current branch, remote state, and the
   requested action; never assume every task is first publication.
3. If a reliable type, target owner/repository, or action cannot be determined,
   ask one focused question and remain read-only.
4. A task-type label never grants a write. Apply the matching authorization
   gate and local report contract separately.
5. For any write-capable route whose exact manifest or diff contains
   .github/workflows/**, load workflow-scope-preflight.md and complete its
   protocol/credential permission gate before repository creation or push.

| Signal | Route |
|---|---|
| inventory, status, audit, or plan only | `DISCOVERY_ONLY` or `PRE_PUBLISH_AUDIT` |
| no verified remote or empty approved target | `INITIAL_PUBLICATION` |
| existing remote and local changes | `PROJECT_UPDATE` or `BRANCH_AND_PR_UPDATE` |
| inspect a PR without changing it | `PR_REVIEW` |
| merge a named PR | `PR_MERGE` |
| review or merge dependency updates | `DEPENDABOT_REVIEW` / `DEPENDABOT_MERGE` |
| tag, notes, or release assets | `RELEASE_PUBLICATION` |
| change owner/origin | `REMOTE_MIGRATION` |
| credentials, 401, 403, token conflict | `AUTH_DIAGNOSIS` / `AUTH_REMEDIATION` |
| approved logo/cover update | `VISUAL_ASSET_PUBLICATION` |
| platform error or checkpoint recovery | `INCIDENT_RECOVERY` |
