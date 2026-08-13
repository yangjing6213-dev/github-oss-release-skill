# 全局中文结果政策 V2.2

```text
CHINESE_RESULT_POLICY_VERSION = 2.2
SKILL_VERSION = 2.2.0
```

本文件适用于首次发布、后续更新、Pull Request、Dependabot、CI/CodeQL、认证、视觉资产、Release、本地标准化、安全审计和只读检查。它只规定最终结果的表达与状态计算，不授权任何 GitHub 写入，也不改变其他安全规则。

## 目录

- [不可覆盖的边界](#不可覆盖的边界)
- [输出前状态计算](#输出前状态计算)
- [固定输出顺序](#固定输出顺序)
- [用户结果摘要](#用户结果摘要)
- [主要检查结果](#主要检查结果)
- [需要处理的问题](#需要处理的问题)
- [状态选择](#状态选择)
- [技术详情与报告](#技术详情与报告)
- [敏感信息与术语](#敏感信息与术语)
- [一致性检查](#一致性检查)
- [场景回归测试](#场景回归测试)

## 不可覆盖的边界

- 继续执行 `SKILL.md`、`pre-publish-gates.md`、`local-reports-and-resume.md` 和当前任务 reference 中所有安全、隐私、许可证、来源、质量和平台闸门。
- `APPROVE_GITHUB_PUBLISH`、本地且被 Git 忽略的 `PRE-PUBLISH-REPORT.md`、`READY_TO_PUBLISH=YES`、目标与动作精确批准仍是写入前置条件。
- 不得弱化 Secret/隐私/License/第三方资产扫描、GitHub 账号检查、Push Protection、Force Push 禁止、CI/CodeQL、平台限制停止、人工确认、最小权限或精确 staging。
- 中文化不是继续写入、绕过阻断、补造证据或把未验证项写成通过的理由。
- 用户另有最终字段清单时，先应用本政策的中文部分，再把用户要求的机器字段原名放入技术详情。

## 输出前状态计算

先识别 `TASK_TYPE`，再按以下顺序计算，不能只看单一字段。

可用任务类型：

```text
DISCOVERY_ONLY
PRE_PUBLISH_AUDIT
INITIAL_PUBLICATION
PROJECT_UPDATE
BRANCH_AND_PR_UPDATE
PR_REVIEW
PR_MERGE
DEPENDABOT_REVIEW
DEPENDABOT_MERGE
RELEASE_PUBLICATION
REMOTE_MIGRATION
AUTH_DIAGNOSIS
AUTH_REMEDIATION
VISUAL_ASSET_PUBLICATION
BADGE_AUDIT
BADGE_UPDATE
PORTFOLIO_BADGE_AUDIT
PORTFOLIO_BADGE_ROLLOUT
INCIDENT_RECOVERY
```

徽章任务必须区分“当前已有徽章”“可以立即添加”“需要先配置”“不适用”、
“不推荐”和“失效或错误徽章”，并给出最终推荐顺序及是否需要授权新增质量能力。
允许的徽章证据状态为 `VERIFIED_READY`、`REQUIRES_QUALITY_SETUP`、
`NOT_APPLICABLE`、`NOT_RECOMMENDED` 和 `BLOCKED_INVALID_EVIDENCE`。徽章评估
默认只读，不因缺少 CI、CodeQL 或 Coverage 自动创建 Workflow。

### 1. 分开保存两个状态

- 仓库既有状态与当前任务状态必须分开计算。
- 仓库状态回答 repository、commit、branch、PR、tag、release 等远程事实是否已经发生。
- 当前任务状态回答本轮目标是否完成、暂停、失败或等待检查。
- 后续维护任务失败不得把已发布仓库写成“项目尚未发布”。
- `READY_TO_PUBLISH=NO` 不能覆盖 `REPOSITORY_PUBLISHED=YES`；它只说明当前准备状态或当前任务存在阻断。

### 2. 状态优先级

按以下优先级保留事实：

1. 已经发生的远程事实：repository 创建、普通 push、PR 创建/合并、tag 或 release 发布、远程 commit 匹配。
2. 当前自动检查结果：CI、CodeQL、依赖审计、tests、lint、typecheck、build。
3. 当前任务的准备状态：`READY_TO_PUBLISH`、`LOCAL_OPEN_SOURCE_READY`、`GITHUB_AUTH_READY`、本地报告或当前阻断。

检查结果内部优先级：`FAIL` 高于 `PENDING`，`PENDING` 高于 `PASS`，`PASS` 高于 `NOT_VERIFIED`。低优先级状态不得抹掉高优先级事实。

### 3. 确定本轮 GitHub 变化

综合检查本轮的 `GITHUB_WRITE_PERFORMED`、`REPOSITORY_CREATED`、`NORMAL_PUSH`、`PR_CREATED`、`PR_MERGED`、`TAG_CREATED`、`RELEASE_CREATED`，使用已经验证的最具体事实。只读或本地任务应明确“没有变化”。

### 4. 确定用户操作

- 存在阻断、失败、人工确认或尚未批准的必要动作时写“需要”。
- 任务完成或只需等待平台自动检查且用户无需操作时写“不需要”。
- 只给一个主要下一步。选择能关闭最高优先级阻断或完成当前任务的一个动作；不要堆叠并列建议。

### 5. GitHub Actions 工作流权限阻断

当 `WORKFLOW_SCOPE_PREFLIGHT_REQUIRED = YES` 且
`WORKFLOW_SCOPE_STATUS = MISSING` 或 `NOT_VERIFIED` 时，状态使用：

`GitHub Actions 工作流权限尚未准备完成`

结论必须说明项目包含工作流文件、计划通过 HTTPS 凭据推送，且已在
创建远程仓库或更新 Push 前停止。保留 `REPOSITORY_CREATED = NO`、
`GITHUB_WRITE_PERFORMED = NO`。下一步只写：授权为当前正确账号补充
workflow scope。不得写“仓库创建失败”或“项目已发布”。

## 固定输出顺序

最终回答必须按此顺序：

1. `# 用户结果摘要`
2. `## 主要检查结果`
3. `## 需要处理的问题`，仅当确有阻断、失败、待确认或后续必要操作时显示
4. `## 技术详情`
5. `## 报告位置`，仅当本轮确实生成本地报告时显示

不得把技术详情或英文状态放在中文摘要之前。用户摘要建议为 8 至 20 行；完整日志、完整依赖清单和内部审计细节放到报告，不在摘要重复。

## 用户结果摘要

使用以下结构并填入真实结果：

```markdown
# 用户结果摘要

任务：
[简体中文任务说明]

状态：
[一个明确中文状态]

结论：
[用 1 至 3 句话区分仓库事实和本轮结果]

GitHub 是否发生变化：
[没有变化 / 已创建仓库 / 已推送代码 / 已创建更新分支 / 已创建 Pull Request / 已合并更新 / 已发布 Release]

是否需要用户继续操作：
[不需要 / 需要]

下一步：
[一个最主要、可直接执行的动作]

相关地址：
[实际地址；没有则为“不适用”或“尚未创建”]
```

状态标题不得只写 `PASS`、`FAIL`、`BLOCKED` 或 `PARTIAL`。部分完成时在结论中分别列出“已完成”和“未完成”，仍只保留一个主要下一步。

## 主要检查结果

中文摘要后输出动态表格，只列与当前任务有关且有证据的项目。不得硬编码测试数量、覆盖率、项目类型、工具、账号、仓库、PR 编号或 commit。

| 检查项目 | 结果 | 说明 |
|---|---|---|
| [当前检查项] | [通过/未通过/已完成/尚未完成/正在运行/不适用/需要复核/已安全暂停] | [简体中文证据摘要] |

未运行、缺少依赖或只运行子集不能写“通过”。检查状态仍在运行时不得写“全部通过”。

## 需要处理的问题

仅在确实存在问题或必要后续动作时显示，最多优先展示三个关键项：

```markdown
### 问题 1：[简短中文名称]

问题：
[普通用户能理解的说明]

影响：
[为何阻断或需要复核]

解决方式：
[一个明确动作]
```

其他低优先级项放入技术详情或本地报告。不要把多个解决动作重新堆成第二份待办清单。

## 状态选择

优先使用以下中文状态，并按远程事实、检查状态、当前任务状态组合判断：

| 条件 | 中文状态 | 关键结论 |
|---|---|---|
| 首次发布远程事实成立，主要检查通过 | 项目已成功发布 | 仓库和代码已经存在于 GitHub |
| 仓库已发布，无失败项且检查仍运行 | 项目已发布，GitHub 正在自动检查 | 等待检查，不重复推送或建仓库 |
| 仓库已发布，任一主要检查失败 | 项目已发布，但自动检查未通过 | 仓库仍存在，以新正常提交修复 |
| 尚无远程写入且发布前阻断 | 项目尚未发布，已被安全规则暂停 | 当前没有创建或推送仓库 |
| 本地准备通过但没有发布事实 | 项目准备完成，等待正式发布 | 本轮未上传 GitHub |
| PR 已创建但未合并 | 项目更新已提交，等待合并 | 主分支尚未改变 |
| PR 已合并且检查通过 | 项目更新已成功合并 | 更新已进入主分支 |
| PR 已合并且检查仍运行 | 项目更新已合并，GitHub 正在自动检查 | 合并事实不被 pending 覆盖 |
| PR 已合并但检查失败 | 项目更新已合并，但自动检查未通过 | 以新提交修复，不撤销合并事实 |
| Dependabot 只读审查完成 | 依赖更新审查已完成 | 没有合并或修改 PR |
| 徽章评估证据已完成 | 徽章评估已完成 | 已分开输出当前徽章、可立即添加、需配置、不适用、不推荐和失效项 |
| 徽章更新已完成本地准备 | 徽章更新已准备完成 | 等待精确范围和更新授权 |
| 徽章远程更新事实成立 | 项目徽章已成功更新 | 仅在远程写入和验证事实成立时使用 |
| 徽章缺少质量能力 | 项目可以获得更多徽章，但需要先建设质量能力 | 不自动创建质量 Workflow |
| Dependabot 合并及合并后检查通过 | 依赖更新已安全合并 | 指定更新已经合并 |
| 认证就绪且环境 Token 不冲突 | GitHub 登录认证已恢复正常 | GitHub 仓库没有变化 |
| 认证未就绪、账号不匹配或环境 Token 冲突 | GitHub 认证仍需处理 | 解释 401/403 等中文含义 |
| Manifest 含工作流且 HTTPS 凭据缺少或未确认 workflow scope | GitHub Actions 工作流权限尚未准备完成 | 创建仓库或 Push 前停止，等待独立权限授权 |
| 本地视觉资产已生成且需人工复核 | 视觉资产已生成，等待人工确认 | 尚未提交或推送 |
| 视觉资产发布事实成立 | 视觉资产已成功更新到 GitHub | 仅在远程事实已验证时使用 |
| 本地标准化完成 | 本地开源整理已完成 | 不等于已经发布 |
| 已发布仓库的后续任务被阻断 | 当前任务已安全暂停 | 明确仓库此前已发布，本轮暂停不撤销它 |
| 本地或只读任务完成且无写入 | 当前任务已完成，GitHub 仓库没有变化 | 不误报远程发布或更新 |
| 部分完成且仍有必要阻断 | 当前任务部分完成，仍有问题需要处理 | 分开列已完成和未完成 |

如果远程事实、检查状态或证据不足，使用“需要复核”或“尚未完成验证”，不得猜测。

## 技术详情与报告

### 技术详情

`## 技术详情` 必须存在，并位于中文摘要、主要检查结果和可选问题之后。把本轮已经产生或用户要求的英文机器字段以原名、原值放入 `text` 代码块；不得删除、改名或只保留对结论有利的字段。

```text
TASK_TYPE = [实际任务类型]
REPOSITORY_PUBLISHED = [实际值]
GITHUB_WRITE_PERFORMED = [实际值]
READY_TO_PUBLISH = [实际值或 NOT_APPLICABLE]
```

机器字段用于自动化、审计、调试和后续任务，不替代中文结论。没有证据的字段使用 `NOT_VERIFIED`、`NOT_APPLICABLE` 或任务既有约定值，不得伪造 `YES`/`PASS`。

### 报告位置

只有本轮确实生成本地报告时才显示 `## 报告位置`。列出帮助用户定位的实际报告路径及必要的 ignored/untracked/unstaged 说明；不得把内部临时目录塞入普通用户摘要。没有报告时省略此节，不创建占位文件。

## 敏感信息与术语

### 敏感信息

用户摘要、技术详情、问题和报告路径中都不得显示 Token、PAT、API key、密码、Cookie、Session、SSH 私钥、恢复码、Secret hash、Secret 前后缀或完整私人邮箱。不得为说明错误而回显凭据。

Commit SHA 默认只显示前 7 至 10 位，除非用户明确要求完整值。本地绝对路径只在确实帮助用户操作时显示。

### 状态中文映射

| 技术状态 | 用户可读表达 |
|---|---|
| PASS | 通过 |
| FAIL | 未通过 |
| PENDING | 正在运行 |
| YES | 是 / 已完成 |
| NO | 否 / 未完成 |
| BLOCKED | 已被安全暂停 |
| NOT_APPLICABLE | 不适用 |
| NOT_CONFIGURED | 尚未配置 |
| NOT_VERIFIED | 尚未完成验证 |
| HTTP 401 | GitHub 登录凭据无效 |
| HTTP 403 | GitHub 拒绝当前访问请求 |
| HTTP 404 | 目标仓库或资源不存在 |
| HTTP 429 | GitHub 请求过于频繁，需要稍后再试 |
| Non-fast-forward | 远程仓库已有更新，不能直接覆盖 |
| Push Protection | GitHub 检测到疑似密钥，已阻止推送 |
| Merge Conflict | 当前更新与主分支存在冲突，不能直接合并 |
| Rate Limit | GitHub 接口调用次数已达到限制 |
| Account Restricted | 当前账号受到 GitHub 访问限制 |

普通用户摘要优先使用“第一个干净提交”“当前版本编号”“发布文件清单”“项目工作目录”“安全同步到最新版本”“将一次更新合并为一个简洁提交”“GitHub CLI 安全保存的登录凭据”“直接复制到项目中的第三方代码”“间接依赖”“文件含义变化”。技术原词可放在技术详情。

遇到 `403` 时只陈述已验证的凭据来源和错误类别；旧环境 Token 的 `403` 不能证明目标新账号被暂停。

## 一致性检查

输出前执行一致性检查。发现冲突时重新计算状态，不得先输出再解释：

- “项目已成功发布”不能同时配“没有上传到 GitHub”。
- “项目尚未发布”不能与 `REPOSITORY_PUBLISHED=YES` 并存。
- “不需要”不能配要求用户修复的下一步。
- “正在运行”不能配“所有自动检查已经通过”。
- “没有 GitHub 写入”不能与 `GITHUB_WRITE_PERFORMED=YES` 并存。
- Dependabot、认证、视觉或只读后续任务的失败不能抹掉仓库既有发布事实。
- 旧凭据路径返回 `403` 不能直接推出新账号被暂停。
- workflow scope 缺失时不能写“仓库创建失败”，因为创建动作尚未发生。
- `APPROVE_GITHUB_PUBLISH` 不能写成已授权 `APPROVE_GITHUB_WORKFLOW_SCOPE_REFRESH`。
- 用户摘要中的 GitHub 变化必须与远程事实和机器字段一致。
- 每个最终结果只给一个主要下一步；模糊的“视情况而定”“可以考虑”不合格。

## 场景回归测试

修改本政策或状态规则后运行：

```powershell
python scripts/validate_chinese_result_policy.py
```

验证器必须覆盖以下场景：

1. 首次发布成功。
2. 仓库已发布且 CI pending。
3. 仓库已发布且 CI fail。
4. 尚未发布且被安全阻断。
5. 本地就绪但未发布。
6. PR 已创建但未合并。
7. PR 已合并且检查通过。
8. Dependabot 只读审查完成。
9. Dependabot 安全合并完成。
10. 认证冲突已修复。
11. 认证仍被阻断。
12. 视觉资产等待人工复核。
13. 已发布仓库的后续任务被阻断，仍保留既有发布事实。
14. 无 GitHub 写入的本地或只读任务完成。
15. Manifest 含工作流、HTTPS OAuth scope 缺失，创建仓库前安全停止。

全部场景通过后才可输出 `GLOBAL_SKILL_VALIDATION = PASS`。结构验证还必须确认中文摘要存在且最先、技术详情存在、机器字段保留、单一明确下一步、无状态矛盾、无硬编码项目或账号、无敏感信息输出。
