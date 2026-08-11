# PRE-PUBLISH-REPORT contract

Create this local-only file before any GitHub write. Use either `<project-root>/PRE-PUBLISH-REPORT.md` or `<project-root>/.local-audit/PRE-PUBLISH-REPORT.md`. The selected path must be Git-ignored, untracked and unstaged; it must not be part of the public repository manifest, commit or push. An ignored report is not missing when the exact selected path exists, is readable and contains complete evidence. If the report is absent, generate it locally only when the user authorizes that action. Keep secrets, tokens and matched secret values out of the report.

```markdown
# Pre-Publish Report

- Generated (local time and timezone):
- Project root:
- Current commit:
- Branch/tag:
- Remote (redacted):
- Intended GitHub owner/repository:
- Intended visibility:
- Proposed approved writes (explicit list): none
- Local report path:
- Git-ignore evidence (`git check-ignore -v`):
- Untracked/unstaged/public-manifest exclusion evidence:
- Skill version: 2.0.0
- Visual asset policy: OPTIONAL_BY_PROJECT
- GITHUB_PUBLISH_APPROVAL_GRANTED: NO
- READY_TO_PUBLISH: NO

## Scope and worktree
- User request and assumptions:
- `git status --short` summary:
- Unrelated/pre-existing changes preserved:

## Required repository files
| Path | Present/changed | Content and validation evidence | Blocker |
|---|---|---|---|

## Secret and history scan
- Tool/version and configuration:
- Worktree/index/all refs/history coverage:
- Result summary (never values):
- Remediation or rotation status:

## Large files and generated content
- Thresholds:
- Findings and Git LFS status:

## Third-party licenses and provenance
- Dependency/assets/models/data inventory:
- Tool/version and findings:
- Attribution/authorization evidence:

## Visual asset decision
- Project type and presentation needs:
- VISUAL_ASSETS_REQUIRED:
- VISUAL_ASSETS_STATUS:
- README active image references and validation:
- Included-asset provenance, rights, privacy and authenticity evidence, or why not applicable:

## Quality gates
| Check | Command | Exit code | Result/evidence |
|---|---|---:|---|

## GitHub read-only and platform checks
- Commands, timestamps and non-secret results:
- Policy sources and version/date checked:
- Restrictions, rate limits or permission errors:

## Blockers and decisions
- Verified facts:
- Inferences or unknowns:
- User decisions required:
- Blocking conditions and closure steps:

## Final gate
`READY_TO_PUBLISH` expresses technical, legal, security and target readiness. Set it to `YES` only when every required check is evidenced and all blockers are closed. Before any GitHub write, re-verify that the selected local report is ignored, untracked, unstaged and excluded from the public manifest. GitHub writes remain forbidden until `GITHUB_PUBLISH_APPROVAL_GRANTED=YES`, which requires the user to supply exact `APPROVE_GITHUB_PUBLISH` in the same release context and approve the listed targets and actions. Never stage, commit or push this report.
```
