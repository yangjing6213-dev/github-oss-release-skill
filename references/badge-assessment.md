# Badge assessment

`scripts/assess_badges.py` is read-only. It accepts a project root, owner,
repository, default branch, optional verified GitHub metadata JSON, and an
optional public manifest. It never edits README files or contacts a write API.

The JSON result includes:

`project_name`, `owner`, `repository`, `default_branch`, `current_badges`,
`eligible_badges`, `badges_requiring_setup`, `not_applicable_badges`,
`not_recommended_badges`, `broken_badges`, `old_owner_badges`,
`duplicate_badges`, `recommended_badge_order`, and
`recommended_badge_count`.

Evidence rules:

- CI/Tests require a root `.github/workflows/*.yml` or `.yaml` and a successful
  run record in supplied metadata.
- License requires `LICENSE`, `LICENSE.txt`, `COPYING`, or verified license
  metadata.
- Release and Tag require verified release/tag metadata; a Tag does not imply a
  Release.
- Version/runtime requires an authoritative package or Skill metadata file.
- Coverage requires a real coverage service or public endpoint.
- CodeQL and Dependency Audit require their real workflow and a successful run.

`BADGES_READY_NOW` and `QUALITY_GATES_RECOMMENDED` stay separate. The script
does not create quality workflows and always returns `github_write_performed:
false`.
