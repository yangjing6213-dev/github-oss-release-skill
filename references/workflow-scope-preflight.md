# Workflow scope preflight

Apply this gate before the first remote mutation whenever an exact publish
manifest or update diff may include GitHub Actions workflow files. Never wait
for a push failure to discover a known permission gap.

## Manifest and push identity

Detect workflow files only from the final exact manifest. Normalize paths to
POSIX form and match repository-root .github/workflows/**; do not count
examples, templates, local reports, or excluded paths.

Record WORKFLOW_FILES_PRESENT, WORKFLOW_FILE_COUNT, WORKFLOW_FILE_PATHS,
PLANNED_PUSH_PROTOCOL, PUSH_CREDENTIAL_SOURCE, PUSH_CREDENTIAL_TYPE,
PUSH_CREDENTIAL_SOURCE_MATCH, OAUTH_SCOPES_INSPECTABLE, and
WORKFLOW_SCOPE_STATUS.

Derive PLANNED_PUSH_PROTOCOL from the final planned push remote, not a stale
current remote. Use HTTPS, SSH, OTHER, NOT_CONFIGURED, or NOT_VERIFIED.
Classify the credential source as GH_TOKEN_ENVIRONMENT,
GITHUB_TOKEN_ENVIRONMENT, GH_CLI_KEYRING, GIT_CREDENTIAL_MANAGER, SSH_KEY,
OTHER, or NOT_VERIFIED. Never expose credential values, lengths, prefixes,
suffixes, or hashes.

Scope evidence is valid only for the credential that the final push will
actually use. If an environment token masks the keyring, keyring scopes cannot
prove that environment token. Set PUSH_CREDENTIAL_SOURCE_MATCH = NO and stop.

## Applicability

Set WORKFLOW_SCOPE_PREFLIGHT_REQUIRED = YES only when the manifest contains
workflow files and the plan is GitHub.com HTTPS using OAuth or a classic PAT.

| Condition | WORKFLOW_SCOPE_STATUS |
|---|---|
| no workflow files | NOT_APPLICABLE_NO_WORKFLOW_FILES |
| SSH push | NOT_APPLICABLE_SSH_PUSH |
| non-GitHub.com host | NOT_APPLICABLE_OR_REQUIRES_HOST_SPECIFIC_POLICY |
| fine-grained PAT or GitHub App | CREDENTIAL_TYPE_SPECIFIC_PERMISSION_REVIEW |
| applicable credential contains workflow | PRESENT |
| inspectable applicable scopes omit it | MISSING |
| credential type, source, or scopes cannot be verified | NOT_VERIFIED |

Type-specific credentials require their own verified repository/workflow
permission check. If no reliable check exists, stop with
WORKFLOW_PERMISSION_NOT_VERIFIED; never pretend OAuth scope rules apply.

## Hard gates

For INITIAL_PUBLICATION, when preflight is required and status is not PRESENT,
set WORKFLOW_SCOPE_PREFLIGHT_RESULT = FAIL,
REPOSITORY_CREATION_ALLOWED = NO, PUSH_ALLOWED = NO,
READY_TO_PUBLISH = NO, and STOP_REASON = WORKFLOW_SCOPE_PREFLIGHT_FAILED.

Do not create an empty repository, configure a remote for a trial push, remove
workflow files, silently switch to SSH, or rely on publish approval to waive
this gate.

For PROJECT_UPDATE, BRANCH_AND_PR_UPDATE, VISUAL_ASSET_PUBLICATION, or
RELEASE_PUBLICATION, apply the same decision to any changed workflow path
before push. Preserve an existing remote repository fact, but set
WORKFLOW_SCOPE_CHECK_BEFORE_PUSH = FAIL and PUSH_ALLOWED = NO.

## Refresh authorization and drift

When status is MISSING, set WORKFLOW_SCOPE_REFRESH_REQUIRED = YES.
APPROVE_GITHUB_PUBLISH does not authorize credential changes. Only exact
APPROVE_GITHUB_WORKFLOW_SCOPE_REFRESH permits one
gh auth refresh --hostname github.com --scopes workflow attempt for the
already verified account. Never perform refresh from inspection scripts.

After a permitted refresh, recheck account identity, credential source match,
and scope status. Before push, recheck manifest paths, protocol, source, scope,
account, and remote owner. Any change invalidates the old evidence and requires
a new preflight.
