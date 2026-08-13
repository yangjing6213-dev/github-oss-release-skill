# Evidence-first badge policy

`BADGE_POLICY = EVIDENCE_FIRST` is mandatory. A badge is a public factual
claim, not decoration. Recommend it only when the project has current,
verifiable evidence for the exact owner, repository, branch, workflow, release,
license, version, runtime, or quality source.

## Classes and statuses

| Class | Examples | Default |
|---|---|---|
| `STATUS_BADGE` | CI, Tests, CodeQL, Coverage, Dependency Audit | Recommend only with real evidence |
| `METADATA_BADGE` | License, Release, Tag, package/runtime version | Recommend when metadata is authoritative |
| `POPULARITY_BADGE` | Stars, Forks, Downloads, Contributors, Social | Do not recommend unless requested |
| `STATIC_CLAIM_BADGE` | passing, secure, maintained, coverage number, quality grade | Do not use for verifiable state |

Every candidate uses one of: `VERIFIED_READY`, `REQUIRES_QUALITY_SETUP`,
`NOT_APPLICABLE`, `NOT_RECOMMENDED`, or `BLOCKED_INVALID_EVIDENCE`.

Default README order is CI/Tests, License, Release/Tag/version, runtime,
CodeQL/security, Coverage, then Dependency Audit. Recommend 2 to 6 badges;
deduplicate badges with the same meaning. A missing quality capability is a
setup recommendation, not permission to create a Workflow.

Never invent status, coverage, version, downloads, tests, CodeQL, Release, or
license evidence. Never use a local image, absolute path, token query string,
old owner/repository, or static `passing`/`secure` claim as a substitute.
