# GitHub 开源项目安全发布 Skill

[English](README.en.md)

`github-oss-release` 是一个社区开源 Codex Skill，用本地证据和只读 GitHub
证据辅助审计、首次发布、后续更新、迁移、PR/Dependabot 审查、合并和
Release 发布。当前 Skill 版本为 `2.1.0`。

它不是 GitHub 或 OpenAI 的官方产品，也不代表 GitHub 或 OpenAI。它不能保证
账号永不受限，也不会自动执行 Star、Fork、Follow、Issue、PR 或 Comment。

## 解决的问题

- 区分本地准备完成、远程仓库事实和当前任务结果。
- 在处理脏工作区、旧历史、秘密、许可证、CI 和认证冲突时默认拒绝危险写入。
- 要求精确文件清单、仅本地发布报告和逐项授权，避免误提交隐私数据或报告。
- 在工作流文件发生变化时，将 HTTPS 推送凭据与 `workflow` scope 证据绑定并提前预检。
- 在 401、403、429、Push Protection、非快进和目标不明时停止，而不是绕过平台限制。

## 支持的任务类型

`DISCOVERY_ONLY`、`PRE_PUBLISH_AUDIT`、`INITIAL_PUBLICATION`、
`PROJECT_UPDATE`、`BRANCH_AND_PR_UPDATE`、`PR_REVIEW`、`PR_MERGE`、
`DEPENDABOT_REVIEW`、`DEPENDABOT_MERGE`、`RELEASE_PUBLICATION`、
`REMOTE_MIGRATION`、`AUTH_DIAGNOSIS`、`AUTH_REMEDIATION`、
`VISUAL_ASSET_PUBLICATION` 和 `INCIDENT_RECOVERY`。

任务类型只负责路由，不代表已经授权 GitHub 写入。

## 安装

使用可信的 Codex Skill Installer 导入本仓库根目录，或将仓库完整复制到 Codex
的 Skills 目录并命名为 `github-oss-release`。安装后确认以下内容存在：

- `SKILL.md`
- `agents/`
- `references/`
- `scripts/`
- `templates/`
- `tests/`

不要把凭据写入仓库 URL、配置、日志或 Skill 文件。安装完成后在新任务中调用。

## 调用

在 Codex 任务中明确写出 Skill 名称、一个任务类型、目标 owner/repository 和预期动作：

```text
Use $github-oss-release
TASK_TYPE = PRE_PUBLISH_AUDIT
Target = <owner>/<repository>
Action = audit only; no GitHub write
```

如果任务类型、目标或动作无法验证，Skill 应提出一个聚焦问题并保持只读。

## 常用操作提示词

先打开真实项目根目录，在 Codex 中新建任务并调用 `$github-oss-release`。把
`<github-owner>`、`<repository-name>`、`<owner/repository>` 和
`<public-or-private>` 替换为目标信息。建议先做只读发布前检查，检查通过后再授权
普通 Push；不要使用 Force Push。本地 PRE/POST/UPDATE 报告会保持忽略，不进入公开仓库。

### 1. 推送前检查

```text
$github-oss-release

TASK_TYPE = PRE_PUBLISH_AUDIT

对当前项目执行完整 GitHub 发布前检查。

目标 GitHub 账号：
<github-owner>

目标仓库名称：
<repository-name>

本轮只读。生成仅保存在本地的 PRE-PUBLISH-REPORT，禁止修改项目、Commit、Push
或任何 GitHub 写入。优先使用简体中文返回结果。
```

### 2. 新项目首次推送

第一步，准备并生成本地报告：

```text
$github-oss-release

TASK_TYPE = INITIAL_PUBLICATION

对当前项目执行首次 GitHub 开源发布准备。

目标 GitHub 账号：
<github-owner>

目标仓库名称：
<repository-name>

目标仓库可见性：
<public-or-private>

本轮不 Commit、不创建远程仓库、不 Push。
```

第二步，仅在 `READY_TO_PUBLISH = YES` 且状态未漂移时授权：

```text
$github-oss-release

APPROVE_GITHUB_PUBLISH

继续当前 INITIAL_PUBLICATION 任务。

授权 GitHub 账号：
<github-owner>

授权目标仓库：
<owner/repository>

授权仓库可见性：
<public-or-private>

只使用精确文件清单、普通 Commit 和普通 Push；禁止 Force Push、覆盖非空仓库、
提交本地报告或创建 Tag/Release。出现高风险问题时立即安全停止。
```

### 3. 已发布项目更新推送

第一步，只准备本次更新：

```text
$github-oss-release

TASK_TYPE = PROJECT_UPDATE

对当前已经发布的 GitHub 项目执行安全更新准备。

目标 GitHub 账号：
<github-owner>

区分本次修改和已有无关修改，检查远程、Workflow、Secret、License 与质量闸门，
生成仅保存在本地的 PRE-PUBLISH-REPORT。本轮不 Commit、不 Push、不创建 Pull Request。
```

第二步，只提交报告已批准的文件：

```text
$github-oss-release

APPROVE_GITHUB_PUBLISH

继续当前 PROJECT_UPDATE 任务。

授权 GitHub 账号：
<github-owner>

只允许提交 PRE-PUBLISH-REPORT 已批准的本次修改。使用精确 Staging 和普通 Push；
main 要求 PR 时创建更新分支和 Pull Request，但不得自动合并或绕过保护。
```

- [完整操作提示词](docs/usage-prompts.md)

## 首次发布流程

1. 发现项目结构、版本、真实命令、Git 状态和既有远程。
2. 只记录认证是否存在、账号身份和调用结果，不显示凭据值。
3. 验证目标仓库不存在或为空；非空目标改走既有远程流程，禁止覆盖。
4. 选择保留安全历史、隔离干净工作区或全新公开历史策略。
5. 检查标准文件、秘密/隐私、第三方许可、质量、UTF-8、链接和构建产物。
6. 生成精确相对路径清单与被 Git 忽略的本地 `PRE-PUBLISH-REPORT.md`。
7. 仅当报告为 `READY_TO_PUBLISH = YES` 且用户提供精确
   `APPROVE_GITHUB_PUBLISH` 时，才允许按清单暂存、普通提交和普通推送。
8. 远程写入后重新验证目标、提交、CI/CodeQL/Dependabot 状态并输出中文结果。

本 Skill 禁止 `git add .`、`git add -A`、force-push、历史重写和绕过 Push
Protection。历史排除或修复需要单独的 `APPROVE_GIT_HISTORY_REMEDIATION`。

## 后续更新

先比较本地/远程 HEAD、分支、工作区所有权和变更归属。干净且低风险的明确更新
可以选择普通直推；混合、较大或需要审查的更新使用分支和 PR。任何路径都必须
重新运行受影响闸门、生成精确清单并取得与目标和动作一致的授权。若本次更新
修改 `.github/workflows/**`，还必须在 Push 前完成与实际 HTTPS 凭据一致的
`workflow` scope 预检。

## PR 与 Dependabot

- `PR_REVIEW` 和 `DEPENDABOT_REVIEW` 默认只读。
- 合并只限指定 PR，并需要 `APPROVE_GITHUB_PR_MERGE`。
- 逐个检查版本跨度、发布说明、变更文件、依赖关系、CI 和安全风险。
- 一个批准不得扩展到其他 PR、分支、仓库、Release 或设置。

## Remote 迁移

迁移前核对旧/新 owner、仓库状态、历史关系、权限和本地链接。旧 remote 只是证据，
不能被静默采用或重写。非快进或非空目标必须停止，使用正常分支/PR 或安全快进整合，
不得 force-push。

## GitHub 认证冲突

Skill 只记录 `GH_TOKEN`/`GITHUB_TOKEN` 是否设置、CLI/API/SSH 账号身份和调用结果，
不读取或输出 token。环境 token 可能遮蔽安全存储的 CLI 凭据，因此需要在临时干净
子进程中做一次诊断。401、403 或 429 最多做一次诊断并停止；不得轮换账号、IP、
代理或绕过限制。

## 授权词

- `APPROVE_GITHUB_PUBLISH`：指定项目、owner/repository、批准文件、普通提交/推送和写后验证。
- `APPROVE_GITHUB_PR_MERGE`：仅指定 PR。
- `APPROVE_GITHUB_RELEASE`：仅指定 tag/release。
- `APPROVE_GIT_HISTORY_REMEDIATION`：仅指定历史操作。
- `APPROVE_REMOTE_DESTRUCTIVE_CHANGE`：仅指定破坏性远程操作。
- `APPROVE_GITHUB_WORKFLOW_SCOPE_REFRESH`：仅允许为已验证账号刷新一次 `workflow` scope；发布授权不会自动包含它。

授权不能跨 owner、仓库、分支、PR、Release、设置或秘密复用。

## 断点续跑

恢复状态保存在被忽略的 `.local-audit/github-oss-release-state.json`。恢复时比较项目
HEAD 和相关文件哈希，只让输入变化的闸门失效；owner、仓库、分支、批准范围或目标
状态变化时，不得恢复任何写入动作。

## 中文结果反馈

最终结果先输出 `# 用户结果摘要`，再给出中文检查表；仅在确有问题时显示问题，
机器字段放入 `## 技术详情`。仓库既有事实和当前任务状态必须分开，最终只给一个
主要下一步。完整规则见 [中文结果政策](references/chinese-result-policy.md)。

## 测试

项目没有运行时包管理器；验证脚本使用 Python 标准库，YAML 检查可选使用已安装的
PyYAML，否则使用保守的基础语法检查。

```powershell
python scripts/validate_skill.py .
python scripts/run_scenario_tests.py
python scripts/validate_chinese_result_policy.py
python tests/test-scripts.py
python scripts/validate_utf8.py --root .
python scripts/check_markdown_links.py .
python scripts/scan_sensitive_content.py .
```

fallback 敏感内容扫描不等同于 Gitleaks/TruffleHog 的完整工作区、索引、refs 和历史扫描。
只有存在 zip/tar 等构建产物时才运行 `inspect_build_artifacts.py`；没有产物时它应报告
`NOT_CONFIGURED`，不应被改写为通过。

## 安全边界

- 默认 `READ_ONLY`；计划、部分测试、登录或本地文件不是远程发布证据。
- 不显示 token、私有邮箱、Cookie、Session、私钥或私人数据。
- 不自动修复账号、切换凭据、改 remote、删除工作区或绕过平台限制。
- 不承诺 CI、CodeQL、许可证、第三方资产或平台策略在未验证时通过。
- 不用于虚假互动、凭据窃取、恶意基础设施、未授权攻击或未授权个人数据发布。

## License 与支持

本项目采用 [MIT License](LICENSE)，版权归 `ENHE AI Studio`（2026）所有。
贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)，安全漏洞请按 [SECURITY.md](SECURITY.md)
私下报告，普通问题见 [SUPPORT.md](SUPPORT.md)。
