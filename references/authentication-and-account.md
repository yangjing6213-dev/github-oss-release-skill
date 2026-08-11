# Authentication and account

Record only presence, account identity, and call outcome. Never record token
values, lengths, prefixes, hashes, private email, or `gh auth token` output.

## Required evidence

```text
EXPECTED_OWNER
GH_TOKEN_SET
GITHUB_TOKEN_SET
CLI_ACCOUNT
API_ACCOUNT
SSH_ACCOUNT
REMOTE_OWNER
ACCOUNT_MATCH
ENVIRONMENT_TOKEN_CONFLICT
READ_READY
WRITE_READY
STOP_REASON
```

Resolve the target owner in this order: (1) explicit owner in the current turn,
(2) unambiguous project-local configuration, (3) verified CLI account. Treat
`REMOTE_OWNER` as an observation only; do not silently adopt an old remote or
rewrite `origin`.

If `GH_TOKEN` or `GITHUB_TOKEN` exists, mark the corresponding `*_SET` field
without showing any value or derived metadata. Check a temporary clean
subprocess to determine whether an environment token masks keyring/CLI
credentials. Do not change permanent Process/User/Machine variables without
`AUTH_REMEDIATION` and explicit authorization.

Do not run `gh auth token`, `gh auth status --show-token`, `gh auth login`,
`gh auth logout`, or `gh auth switch` as part of this skill. A 401, 403, or 429
gets at most one diagnostic check: do not loop, rotate accounts/tokens/IPs,
proxy-hop, or infer that a different account is suspended from error text.
Classify the actual credential source before reporting the cause.
