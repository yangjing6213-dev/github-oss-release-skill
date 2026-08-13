# GitHub Project Delivery Prompt Recipes

Start a new Codex task from the real project root, invoke
`$github-oss-release`, and replace these placeholders: `<github-owner>`,
`<repository-name>`, `<owner/repository>`, and `<public-or-private>`. Run the
read-only audit first. Authorize an ordinary Push only while the audited state
is unchanged and `READY_TO_PUBLISH = YES`. Never use Force Push. Local reports
must not enter the public repository.

## 1. Pre-push audit

Use this before any GitHub write.

```text
$github-oss-release

TASK_TYPE = PRE_PUBLISH_AUDIT

Run a complete GitHub pre-publication audit for the current project.

Target GitHub account:
<github-owner>

Target repository name:
<repository-name>

This step is read-only.

Check:

- GitHub account, environment Token, CLI/API/SSH identity, and Remote;
- Git worktree and Git history;
- Project architecture and required open-source files;
- Secrets, private data, and local absolute paths;
- License, third-party code, and third-party assets;
- Large files, caches, build artifacts, and local reports;
- README, UTF-8, Markdown links, and YAML;
- Tests, coverage, Lint, type checking, and build commands that actually exist;
- GitHub Actions Workflow permission preflight when applicable;
- The correct publication strategy.

Create a local-only PRE-PUBLISH-REPORT.

This step must not:

- Modify project files;
- Commit;
- Create a GitHub Repository;
- Push;
- Create or merge a Pull Request;
- Create a Tag or Release;
- Perform any GitHub write.

Return the result in Simplified Chinese first.
```

## 2. First push for a new project

### Step one: prepare the initial publication

```text
$github-oss-release

TASK_TYPE = INITIAL_PUBLICATION

Prepare the current project for its first GitHub open-source publication.

Target GitHub account:
<github-owner>

Target repository name:
<repository-name>

Target repository visibility:
<public-or-private>

Requirements:

- Detect the project name, type, version, technology stack, and purpose;
- Check account, environment Token, Remote, worktree, and Git history;
- Check Secrets, privacy, License, third-party content, and large files;
- Add only open-source files the project actually needs;
- Run quality checks that actually exist in the project;
- Select a safe publication strategy;
- Create a local-only PRE-PUBLISH-REPORT;
- Return the result in Simplified Chinese first.

Do not Commit, create the remote repository, or Push in this step.
```

### Step two: perform the first push

```text
$github-oss-release

APPROVE_GITHUB_PUBLISH

Continue the current INITIAL_PUBLICATION task.

Authorized GitHub account:
<github-owner>

Authorized target repository:
<owner/repository>

Authorized repository visibility:
<public-or-private>

Proceed only when:

READY_TO_PUBLISH = YES

and the account, target repository, Remote, public Manifest, and security state
have not changed. Only then may the task:

- Complete low-risk local remediation and revalidation within the authorized scope;
- Stage the exact file manifest;
- Create a safe first commit;
- Create an empty repository when the target does not exist;
- Push the default branch with an ordinary Push;
- Verify remote Commit, README, LICENSE, CI, CodeQL, Dependabot, and source download;
- Create a local-only POST-PUBLISH-REPORT.

Prohibited:

- git add .
- git add -A
- Force Push
- Force Push With Lease
- Overwriting a non-empty repository
- Bypassing Push Protection
- Committing local reports, caches, backups, Tokens, Secrets, or private data
- Creating a Tag or Release

Stop safely when any high-risk condition appears.
```

### 4. Evidence-first badge assessment

```text
$github-oss-release

TASK_TYPE = BADGE_AUDIT

Assess the current project badges read-only. Do not edit README files, create
Workflows, or perform a GitHub write. Return current badges, ready-now badges,
quality setup required, not applicable, not recommended, broken badges, final
recommendation order, and whether authorization is needed for new quality capability.
```

Use `BADGE_UPDATE` only for one named project after assessment and explicit
approval. Portfolio work must use `PORTFOLIO_BADGE_AUDIT` or
`PORTFOLIO_BADGE_ROLLOUT` with an exact repository list; stop the rollout after
the first repository write failure.

## 3. Update push for a published project

### Step one: prepare the update

```text
$github-oss-release

TASK_TYPE = PROJECT_UPDATE

Prepare a safe update for the current published GitHub project.

Target GitHub account:
<github-owner>

Requirements:

- Confirm that the current account, Remote Owner, and target repository match;
- Fetch and compare the latest remote state;
- Separate current-task, pre-existing unrelated, mixed, and unknown changes;
- Handle only files related to this update;
- Check whether this update changes a GitHub Actions Workflow;
- Check Secrets, privacy, License, third-party content, and large files;
- Update affected README, CHANGELOG, and documentation;
- Run tests, Lint, type checking, and build commands that actually exist;
- Select direct Push or Branch + Pull Request automatically and safely;
- Create a local-only PRE-PUBLISH-REPORT;
- Return the result in Simplified Chinese first.

Do not Commit, Push, or create a Pull Request in this step.
```

### Step two: perform the update push

```text
$github-oss-release

APPROVE_GITHUB_PUBLISH

Continue the current PROJECT_UPDATE task.

Authorized GitHub account:
<github-owner>

Commit only current-task changes approved by PRE-PUBLISH-REPORT.

Requirements:

- Confirm that local and remote state has no unaudited drift;
- Use exact file-list Staging;
- Create an accurate Conventional Commit;
- Use an ordinary Push or create an update branch and Pull Request as repository rules require;
- Never bypass protection when main is protected;
- Do not auto-merge a Pull Request without separate explicit authorization;
- Verify remote Commit, README, and CI after the Push;
- Create a local-only UPDATE-REPORT.

Prohibited:

- Committing unrelated changes;
- git add .
- git add -A
- Force Push
- Bypassing Push Protection
- Committing local reports, caches, build artifacts, Secrets, or private data
- Creating a Tag or Release

Stop safely when any high-risk condition appears.
```
