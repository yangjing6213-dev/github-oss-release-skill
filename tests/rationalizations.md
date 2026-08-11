# REFACTOR rationalizations

Only observed baseline reasoning is recorded here; no hypothetical edge cases
were added.

| Observed phrase or shortcut | Risk | v2 counter |
|---|---|---|
| “真实捷径是按影响范围复验并复用与文档无关的既有通过证据。” | Without an invalidation map, stale evidence could be reused. | `project-updates.md` names invalidated gates and requires a fresh final integrity check. |
| “ignored 不等于报告缺失，因此无需重建。” | An ignored report could still be accidentally included in the public manifest. | `local-reports-and-resume.md` and `build_release_manifest.py` treat ignored reports as present local evidence and exclude them from publication. |
| “‘只差 bypass’是临门一脚/沉没成本合理化。” | Push Protection bypass could publish a secret. | `pre-publish-gates.md` requires remediation, rotation, authorized history cleanup, and rescan; bypass is prohibited. |
| “‘已经花了一整天’属于沉没成本，不改变风险。” | Pressure could cause dirty or unlicensed material to be pushed. | `project-updates.md` classifies dirty ownership and stops on mixed/unknown changes. |

`RATIONALIZATIONS_CAPTURED = 4`
