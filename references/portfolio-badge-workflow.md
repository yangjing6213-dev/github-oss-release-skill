# Portfolio badge workflow

Portfolio assessment is read-only by default. Build an explicit repository
list, preserve per-repository evidence, and stop the rollout when a target is
unknown, non-empty in an unexpected way, unauthorized, or returns a platform
error. A failure in one repository must not silently continue writes to later
repositories.

`PORTFOLIO_BADGE_AUDIT` returns per-repository results only. It may recommend
quality setup but never creates it. `PORTFOLIO_BADGE_ROLLOUT` requires an exact
approved repository list, an exact per-repository manifest, a local report with
`READY_TO_PUBLISH = YES`, final drift checks, and ordinary non-force writes.
`STOP_ON_FIRST_WRITE_FAILURE = YES` is mandatory for rollout execution.

Keep `BADGES_READY_NOW` separate from `QUALITY_GATES_RECOMMENDED`. Do not
default to Stars, Forks, Downloads, Social, or static claim badges. Preserve
already-established publication facts when a later repository is blocked.
