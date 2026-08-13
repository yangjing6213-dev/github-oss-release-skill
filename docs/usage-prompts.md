# GitHub 项目发布操作提示词

在真实项目根目录中新建 Codex 任务，调用 `$github-oss-release`，并替换下列
占位符：`<github-owner>`、`<repository-name>`、`<owner/repository>`、
`<public-or-private>`。推荐先执行只读检查，再在状态未变化且
`READY_TO_PUBLISH = YES` 时授权普通 Push。不要使用 Force Push；本地报告不会
进入公开仓库。

## 1. 推送前检查

适合在任何 GitHub 写入前使用。

```text
$github-oss-release

TASK_TYPE = PRE_PUBLISH_AUDIT

对当前项目执行完整 GitHub 发布前检查。

目标 GitHub 账号：
<github-owner>

目标仓库名称：
<repository-name>

本轮只读。

请检查：

- GitHub 账号、环境 Token、CLI/API/SSH 和 Remote；
- Git 工作区与 Git 历史；
- 项目架构与必要开源文件；
- Secret、隐私数据和本地绝对路径；
- License、第三方代码和第三方资产；
- 大文件、缓存、构建产物和本地报告；
- README、UTF-8、Markdown 链接和 YAML；
- 项目真实存在的测试、覆盖率、Lint、类型检查和构建；
- GitHub Actions Workflow 权限预检，适用时；
- 正确的发布策略。

生成仅保存在本地的 PRE-PUBLISH-REPORT。

本轮禁止：

- 修改项目文件；
- Commit；
- 创建 GitHub Repository；
- Push；
- 创建或合并 Pull Request；
- 创建 Tag 或 Release；
- 任何 GitHub 写入。

优先使用简体中文返回结果。
```

## 2. 新项目首次推送

### 第一步：首次发布准备

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

要求：

- 自动识别项目名称、类型、版本、技术栈和用途；
- 检查账号、环境 Token、Remote、工作区和 Git 历史；
- 检查 Secret、隐私、License、第三方内容和大文件；
- 补齐项目真正需要的开源文件；
- 运行项目真实存在的质量检查；
- 自动选择安全发布策略；
- 生成仅保存在本地的 PRE-PUBLISH-REPORT；
- 优先使用简体中文返回结果。

本轮不 Commit、不创建远程仓库、不 Push。
```

### 第二步：正式首次推送

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

只有在：

READY_TO_PUBLISH = YES

并且账号、目标仓库、Remote、公开 Manifest 和安全状态均未变化时，才允许：

- 完成授权范围内的低风险本地整改和复验；
- 使用精确文件清单 Staging；
- 创建安全的第一个提交；
- 目标仓库不存在时创建空仓库；
- 使用普通 Push 推送默认分支；
- 验证远程 Commit、README、LICENSE、CI、CodeQL、Dependabot 和源码下载；
- 生成仅保存在本地的 POST-PUBLISH-REPORT。

禁止：

- git add .
- git add -A
- Force Push
- Force Push With Lease
- 覆盖非空仓库
- 绕过 Push Protection
- 提交本地报告、缓存、备份、Token、Secret 或私人数据
- 创建 Tag 或 Release

出现高风险问题时立即安全停止。
```

### 4. 徽章证据评估

```text
$github-oss-release

TASK_TYPE = BADGE_AUDIT

评估当前项目徽章，只读，不修改 README，不创建 Workflow，不执行 GitHub 写入。
输出当前已有徽章、可以立即添加、需要先配置、不适用、不推荐、失效或错误徽章、
最终推荐顺序，以及是否需要授权新增质量能力。
```

仅在单个项目完成评估并明确批准后使用 `BADGE_UPDATE`。批量任务必须使用
`PORTFOLIO_BADGE_AUDIT` 或 `PORTFOLIO_BADGE_ROLLOUT`，并提供精确仓库列表；
一个仓库失败后不得继续写入其他仓库。

## 3. 已发布项目更新推送

### 第一步：更新准备

```text
$github-oss-release

TASK_TYPE = PROJECT_UPDATE

对当前已经发布的 GitHub 项目执行安全更新准备。

目标 GitHub 账号：
<github-owner>

要求：

- 确认当前账号、Remote Owner 和目标仓库一致；
- 获取并比较远程最新状态；
- 区分本次修改、已有无关修改、混合修改和未知修改；
- 只处理本次更新相关文件；
- 检查本次更新是否修改 GitHub Actions Workflow；
- 检查 Secret、隐私、License、第三方内容和大文件；
- 更新受影响的 README、CHANGELOG 和文档；
- 运行项目真实存在的测试、Lint、类型检查和构建；
- 自动判断使用直接 Push 还是 Branch + Pull Request；
- 生成仅保存在本地的 PRE-PUBLISH-REPORT；
- 优先使用简体中文返回结果。

本轮不 Commit、不 Push、不创建 Pull Request。
```

### 第二步：正式更新推送

```text
$github-oss-release

APPROVE_GITHUB_PUBLISH

继续当前 PROJECT_UPDATE 任务。

授权 GitHub 账号：
<github-owner>

只允许提交 PRE-PUBLISH-REPORT 已批准的本次修改。

要求：

- 确认本地与远程状态没有发生未审计变化；
- 使用精确文件清单 Staging；
- 生成准确的 Conventional Commit；
- 根据项目规则执行普通 Push 或创建更新分支和 Pull Request；
- main 受保护时不得绕过保护；
- 如果创建 Pull Request，不得自动合并，除非另有明确授权；
- 推送后验证远程 Commit、README 和 CI；
- 生成仅保存在本地的 UPDATE-REPORT。

禁止：

- 提交无关修改；
- git add .
- git add -A
- Force Push
- 绕过 Push Protection
- 提交本地报告、缓存、构建产物、Secret 或私人数据
- 创建 Tag 或 Release

出现高风险问题时立即安全停止。
```
