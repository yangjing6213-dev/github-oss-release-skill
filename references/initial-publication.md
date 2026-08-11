# Initial publication

Use only for a verified empty/absent target and an approved scope:

```text
discover → authenticate → inspect remote → compliance → history strategy
→ standard files → secret/privacy/license → quality → exact manifest
→ local PRE-PUBLISH report → authorization → exact staging → commit
→ create empty remote (if needed) → ordinary push → remote verification
→ CI/CodeQL/Dependabot observation → Chinese result
```

Creating an empty repository must not pre-create README, LICENSE, `.gitignore`,
or an initial commit. A non-empty target is not an initial-publication target;
route to `CONTINUE_EXISTING_REMOTE` and never overwrite it.

Use an explicit relative manifest and stage each approved path. Re-read HEAD,
branch, remote, report isolation, target, and the approved action immediately
before each write. A normal publish approval does not authorize a Release,
PR merge, settings change, history rewrite, or force-push.
