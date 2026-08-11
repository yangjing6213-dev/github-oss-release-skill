# Remote migration

Changing a GitHub login does not change a project's `origin`. Record:

```text
OLD_REMOTE
EXPECTED_OWNER
TARGET_REMOTE
TARGET_REPOSITORY_STATUS
```

Keep repository URL/owner, commit author, copyright holder, and historical
facts separate. A migration may update verified clone, badge, issue, and
metadata URLs. It must not silently change `LICENSE` copyright, author
attribution, old commit authors, or unrelated history.

Changing a remote URL is local configuration; pushing to a new owner is a
separate write. Require explicit target confirmation and the relevant approval.
Do not overwrite a non-empty target, delete branches, or force-push without the
separate destructive authorization (and normally stop because force-push is
prohibited by this skill).
