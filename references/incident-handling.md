# Incident handling

| Signal | Safe interpretation | Required response |
|---|---|---|
| 401 | credential used by this request is invalid/expired | inspect token precedence and keyring once; stop |
| 403 / suspended text | GitHub rejected this credential path | correlate identity; do not claim another account is suspended |
| 404 | resource absent only if authentication is verified | verify auth before treating it as non-existent |
| 429 / rate limit | request frequency is restricted | stop and wait; no high-frequency retry |
| non-fast-forward | remote has history not in local HEAD | compare and integrate normally; never force-push |
| Push Protection | suspected secret | remove/rotate, clean authorized history, rescan; never bypass |
| workflow scope missing/unverified | planned HTTPS credential cannot publish manifest workflows | stop before repository creation/push; request separate refresh authorization |
| CI failure | repository may already be published | preserve the remote fact; fix with a new normal change |

Preserve local evidence and the checkpoint state. Do not recreate a repository,
rewrite history, switch accounts, change IP/proxy, or retry around a platform
restriction.
