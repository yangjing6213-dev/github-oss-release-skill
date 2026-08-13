# Badge publication

Use `BADGE_AUDIT` for a single-project read-only assessment and
`PORTFOLIO_BADGE_AUDIT` for a read-only owner portfolio. Use `BADGE_UPDATE` or
`PORTFOLIO_BADGE_ROLLOUT` only after the user names the exact project or
approved repository list.

Badge updates normally touch only `README.md`, `README.en.md`, and required
docs. Keep both language files factually identical. Validate image URL, target
URL, owner, repository, default branch, workflow filename, duplicate meaning,
license/release/tag evidence, and absence of token query parameters.

If the update adds or modifies `.github/workflows/**` to create missing
evidence, stop and apply `workflow-scope-preflight.md`. A publish approval does
not authorize a workflow-scope refresh. Do not create a ceremonial Workflow
just to turn a badge green.

Use exact staging. Never commit local reports, caches, backups, source paths,
private assets, or generated artifacts not present in the approved manifest.
