---
name: github-oss-release
description: Use when preparing, publishing, migrating, updating, reviewing, merging, or releasing a GitHub project, especially when authentication, remotes, dirty worktrees, unsafe history, secrets, licenses, CI, pull requests, Dependabot, or account restrictions may affect safe delivery.
---

# GitHub OSS Release

## Overview

Use this skill to make a GitHub open-source delivery decision from local and
read-only platform evidence. It separates repository facts, the current task,
and local readiness. `SKILL_VERSION = 2.0.0`.

## Highest-Priority Rules

- Default to `READ_ONLY`; inspect before editing and preserve unrelated work.
- Never expose or write secrets, token values, private email, or private data.
- Never use `git add .`, `git add -A`, force-push, history rewrite, or a bypass
  of Push Protection. Stage an explicit manifest only.
- A local plan, passing subset, draft PR, login, or ignored report is not proof
  of a remote release. Stop on missing, stale, contradictory, or unverified
  evidence.
- Stop on 401/403/429, account or policy restrictions, non-fast-forward,
  suspected secrets, dirty mixed ownership, or an unknown target. Do not retry
  around a platform stop.

## Task-Type Router

Set exactly one `TASK_TYPE` before any write:

`DISCOVERY_ONLY`, `PRE_PUBLISH_AUDIT`, `INITIAL_PUBLICATION`,
`PROJECT_UPDATE`, `BRANCH_AND_PR_UPDATE`, `PR_REVIEW`, `PR_MERGE`,
`DEPENDABOT_REVIEW`, `DEPENDABOT_MERGE`, `RELEASE_PUBLICATION`,
`REMOTE_MIGRATION`, `AUTH_DIAGNOSIS`, `AUTH_REMEDIATION`,
`VISUAL_ASSET_PUBLICATION`, or `INCIDENT_RECOVERY`.

Read [workflow-router.md](references/workflow-router.md) first. If the type,
target owner/repository, or requested action cannot be verified, ask one
focused question and perform no GitHub write.

## Required Reference Loading

Always load [workflow-router](references/workflow-router.md),
[repository-discovery](references/repository-discovery.md),
[authentication-and-account](references/authentication-and-account.md),
[pre-publish-gates](references/pre-publish-gates.md),
[local-reports-and-resume](references/local-reports-and-resume.md), and
[chinese-result-policy](references/chinese-result-policy.md). Then load only
the task-specific reference: [repository-standard](references/repository-standard.md),
[publication-strategies](references/publication-strategies.md),
[initial-publication](references/initial-publication.md),
[project-updates](references/project-updates.md),
[pull-requests](references/pull-requests.md),
[dependabot](references/dependabot.md), [releases](references/releases.md),
[remote-migration](references/remote-migration.md),
[incident-handling](references/incident-handling.md), or
[visual-assets-publication](references/visual-assets-publication.md). Use
`pre-publish-report.md` and `required-files.md`/`visual-assets.md` as
compatibility references when an existing project already uses those names.

## Authorization Gates

The default authorization is `READ_ONLY`. Exact, single-task scopes are:

- `APPROVE_GITHUB_PUBLISH`: the named project/owner/repository, approved files,
  ordinary commit/push, and post-write verification.
- `APPROVE_GITHUB_PR_MERGE`: the named PR number only.
- `APPROVE_GITHUB_RELEASE`: the named tag/release only.
- `APPROVE_GIT_HISTORY_REMEDIATION`: the named history operation only.
- `APPROVE_REMOTE_DESTRUCTIVE_CHANGE`: the named destructive remote action.

Each write also needs a complete local report with `READY_TO_PUBLISH = YES`,
an explicit action list, and a final drift check. One approval never expands
to another owner, repository, branch, PR, release, setting, or secret.

## Stop Conditions

Stop and report `GITHUB_WRITE_PERFORMED = NO` when a gate fails, a value is
unknown, a token conflict exists, a target is non-empty, a change is mixed or
unowned, a required test is `NOT_CONFIGURED`, or a platform error occurs.
Do not claim an unpublished project when `REPOSITORY_PUBLISHED = YES` is an
established fact.

## Output Contract

任何最终回答前，完整读取并应用 [references/chinese-result-policy.md](references/chinese-result-policy.md)。不得削弱任何安全闸门。Start with
`# 用户结果摘要`, use a Chinese results table, show problems only when they
exist, then preserve all requested English machine fields under
`## 技术详情`. Show one main next step and a local report path only when a
report was actually created. Keep secrets masked.

## Quick Reference

`DISCOVERY_ONLY` → inspect; `PRE_PUBLISH_AUDIT` → gates/report;
`INITIAL_PUBLICATION` → clean empty remote only; `PROJECT_UPDATE` → direct or
branch/PR; `PR_REVIEW` → read-only; `PR_MERGE`/`DEPENDABOT_MERGE` → named approval;
`RELEASE_PUBLICATION` → release approval; `REMOTE_MIGRATION`/`AUTH_*` → diagnose
before repair; `INCIDENT_RECOVERY` → stop, preserve evidence, resume locally.
