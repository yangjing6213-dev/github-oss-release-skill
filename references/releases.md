# Releases

Creating a tag or GitHub Release requires the exact
`APPROVE_GITHUB_RELEASE`; `APPROVE_GITHUB_PUBLISH` is insufficient. Name the
target tag/release and keep the action one-task scoped.

Before writing, verify `VERSION`, `CHANGELOG`, `TESTS`, `BUILD`, `SECURITY`,
`TAG`, release notes, assets, and `SHA256SUMS` when assets are distributed.
Confirm the tag points at the reviewed commit, no secret or local report enters
the asset set, and the version is not already published. Re-read the commit and
remote state immediately before tag/release creation, then verify the published
tag, notes, assets, and checks without rewriting history.
