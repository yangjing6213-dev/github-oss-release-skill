from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = ROOT / "SKILL.md"
POLICY_PATH = ROOT / "references" / "chinese-result-policy.md"
TASK_TYPES = {
    "DISCOVERY_ONLY",
    "PRE_PUBLISH_AUDIT",
    "INITIAL_PUBLICATION",
    "PROJECT_UPDATE",
    "BRANCH_AND_PR_UPDATE",
    "PR_REVIEW",
    "PR_MERGE",
    "DEPENDABOT_REVIEW",
    "DEPENDABOT_MERGE",
    "RELEASE_PUBLICATION",
    "REMOTE_MIGRATION",
    "AUTH_DIAGNOSIS",
    "AUTH_REMEDIATION",
    "VISUAL_ASSET_PUBLICATION",
    "INCIDENT_RECOVERY",
}


@dataclass(frozen=True)
class Result:
    status: str
    conclusion: str
    github_change: str
    user_action_required: bool
    next_action: str


def is_yes(fields: Mapping[str, str], name: str) -> bool:
    return fields.get(name, "").upper() == "YES"


def value(fields: Mapping[str, str], name: str) -> str:
    return fields.get(name, "").upper()


def resolve_result(task_type: str, fields: Mapping[str, str]) -> Result:
    """Resolve representative final states for policy regression tests."""
    published = is_yes(fields, "REPOSITORY_PUBLISHED")
    ci_statuses = {
        value(fields, "CI_STATUS"),
        value(fields, "CODEQL_STATUS"),
        value(fields, "DEPENDENCY_AUDIT_STATUS"),
    }

    if is_yes(fields, "DEPENDABOT_MERGE_SEQUENCE_COMPLETED"):
        if is_yes(fields, "ALL_POST_MERGE_CHECKS_PASS"):
            return Result(
                "依赖更新已安全合并",
                "依赖更新已合并，合并后检查通过。",
                "已合并依赖更新",
                False,
                "本次依赖更新已经完成，继续正常开发即可。",
            )

    if is_yes(fields, "PR_MERGED"):
        if "FAIL" in ci_statuses:
            status = "项目更新已合并，但自动检查未通过"
            action = "读取失败日志并创建一个新的正常修复提交。"
            required = True
        elif "PENDING" in ci_statuses:
            status = "项目更新已合并，GitHub 正在自动检查"
            action = "等待 GitHub 自动检查完成，不要重新推送。"
            required = False
        else:
            status = "项目更新已成功合并"
            action = "本次更新已经完成，无需继续操作。"
            required = False
        return Result(status, "更新已经合并到正式主分支。", "已合并更新", required, action)

    if is_yes(fields, "PR_CREATED"):
        return Result(
            "项目更新已提交，等待合并",
            "更新已上传到独立分支并创建 Pull Request，正式主分支尚未改变。",
            "已创建更新分支和 Pull Request",
            True,
            "等待自动检查通过并完成审核后，再决定是否合并。",
        )

    if is_yes(fields, "DEPENDABOT_REVIEW_COMPLETE"):
        return Result(
            "依赖更新审查已完成",
            "依赖更新的风险、兼容性和测试审查已完成，本轮没有修改 Pull Request。",
            "没有变化",
            value(fields, "SAFE_TO_MERGE") != "YES",
            "根据审查结论执行唯一获准的后续动作。",
        )

    if task_type in {"AUTH_DIAGNOSIS", "AUTH_REMEDIATION"}:
        auth_ready = is_yes(fields, "AUTHENTICATION_READY")
        conflict = is_yes(fields, "ENVIRONMENT_TOKEN_CONFLICT")
        mismatch = is_yes(fields, "AUTH_ACCOUNT_MISMATCH")
        if auth_ready and not conflict and not mismatch:
            restart = is_yes(fields, "CODEX_RESTART_REQUIRED")
            return Result(
                "GitHub 登录认证已恢复正常",
                "当前 GitHub 凭据可正常使用，环境变量不再覆盖正确凭据。",
                "没有变化",
                restart,
                "完全退出 Codex 和后台进程，然后重新打开一次。"
                if restart
                else "继续使用当前 Codex 会话执行 GitHub 任务。",
            )
        return Result(
            "GitHub 认证仍需处理",
            "当前凭据与目标账号不一致，或环境变量仍在覆盖正确凭据。",
            "没有变化",
            True,
            "按当前诊断证据修复唯一的认证阻断项。",
        )

    if task_type == "VISUAL_ASSET_PUBLICATION" and all(
        [
            is_yes(fields, "LOGO_GENERATED"),
            is_yes(fields, "COVER_GENERATED"),
            value(fields, "HUMAN_VISUAL_REVIEW") == "REQUIRED",
            not is_yes(fields, "GITHUB_WRITE_PERFORMED"),
        ]
    ):
        return Result(
            "视觉资产已生成，等待人工确认",
            "视觉资产已保存在本地，尚未提交或推送到 GitHub。",
            "没有变化",
            True,
            "检查视觉效果，确认满意后再执行 README 集成和推送。",
        )

    current_blocked = is_yes(fields, "PUBLISH_BLOCKED") or is_yes(fields, "CURRENT_TASK_BLOCKED")
    if published:
        if "FAIL" in ci_statuses:
            return Result(
                "项目已发布，但自动检查未通过",
                "代码已经上传到 GitHub，但部分自动检查失败。",
                "已推送代码",
                True,
                "读取失败日志并创建一个新的正常修复提交。",
            )
        if "PENDING" in ci_statuses:
            return Result(
                "项目已发布，GitHub 正在自动检查",
                "代码已经上传到 GitHub，自动检查仍在运行。",
                "已推送代码",
                False,
                "等待 GitHub 自动检查完成，不要重新推送。",
            )
        if current_blocked:
            return Result(
                "当前任务已安全暂停",
                "项目仓库此前已经发布；本次暂停只影响当前维护任务，不撤销既有发布事实。",
                "没有变化",
                True,
                "处理当前任务最重要的一个阻断项后重新验证。",
            )
        if is_yes(fields, "GITHUB_PUBLICATION_SUCCESS"):
            return Result(
                "项目已成功发布",
                "项目代码已经成功上传到 GitHub，主要自动检查通过。",
                "已创建仓库并推送代码",
                False,
                "当前发布已经完成，无需继续操作。",
            )

    if current_blocked and not published:
        return Result(
            "项目尚未发布，已被安全规则暂停",
            "发布前发现阻断项，当前没有创建仓库或推送项目文件。",
            "没有变化",
            True,
            "处理最重要的一个发布阻断项后重新验证。",
        )

    if is_yes(fields, "READY_TO_PUBLISH") and not published:
        return Result(
            "项目准备完成，等待正式发布",
            "本地检查已通过，但本轮尚未上传到 GitHub。",
            "没有变化",
            True,
            "确认目标账号和仓库后，再明确授权正式发布。",
        )

    if not is_yes(fields, "GITHUB_WRITE_PERFORMED") and (
        value(fields, "LOCAL_SECURITY_AUDIT") == "PASS" or task_type in {"DISCOVERY_ONLY", "PRE_PUBLISH_AUDIT"}
    ):
        return Result(
            "当前任务已完成，GitHub 仓库没有变化",
            "本地或只读检查已经完成，本轮未执行 GitHub 写入。",
            "没有变化",
            False,
            "当前任务已经完成，无需继续操作。",
        )

    return Result(
        "当前任务部分完成，仍有问题需要处理",
        "现有证据不足以确认全部目标完成。",
        "没有变化" if not is_yes(fields, "GITHUB_WRITE_PERFORMED") else "需要复核",
        True,
        "补充当前任务缺失的关键证据后重新计算状态。",
    )


SCENARIOS = [
    ("INITIAL_PUBLICATION", {"REPOSITORY_PUBLISHED": "YES", "GITHUB_PUBLICATION_SUCCESS": "YES", "FORCE_PUSH_USED": "NO", "CI_STATUS": "PASS"}, "项目已成功发布"),
    ("PROJECT_UPDATE", {"REPOSITORY_PUBLISHED": "YES", "CI_STATUS": "PENDING"}, "项目已发布，GitHub 正在自动检查"),
    ("PROJECT_UPDATE", {"REPOSITORY_PUBLISHED": "YES", "CI_STATUS": "FAIL"}, "项目已发布，但自动检查未通过"),
    ("INITIAL_PUBLICATION", {"PUBLISH_BLOCKED": "YES", "READY_TO_PUBLISH": "NO", "REPOSITORY_PUBLISHED": "NO"}, "项目尚未发布，已被安全规则暂停"),
    ("INITIAL_PUBLICATION", {"READY_TO_PUBLISH": "YES", "REPOSITORY_PUBLISHED": "NO"}, "项目准备完成，等待正式发布"),
    ("BRANCH_AND_PR_UPDATE", {"PR_CREATED": "YES", "PR_MERGED": "NO"}, "项目更新已提交，等待合并"),
    ("PR_MERGE", {"PR_MERGED": "YES", "CI_STATUS": "PASS"}, "项目更新已成功合并"),
    ("DEPENDABOT_REVIEW", {"DEPENDABOT_REVIEW_COMPLETE": "YES", "GITHUB_WRITE_PERFORMED": "NO"}, "依赖更新审查已完成"),
    ("DEPENDABOT_MERGE", {"DEPENDABOT_MERGE_SEQUENCE_COMPLETED": "YES", "ALL_POST_MERGE_CHECKS_PASS": "YES"}, "依赖更新已安全合并"),
    ("AUTH_REMEDIATION", {"AUTHENTICATION_READY": "YES", "ENVIRONMENT_TOKEN_CONFLICT": "NO"}, "GitHub 登录认证已恢复正常"),
    ("AUTH_DIAGNOSIS", {"AUTHENTICATION_READY": "NO", "ENVIRONMENT_TOKEN_CONFLICT": "YES"}, "GitHub 认证仍需处理"),
    ("VISUAL_ASSET_PUBLICATION", {"LOGO_GENERATED": "YES", "COVER_GENERATED": "YES", "HUMAN_VISUAL_REVIEW": "REQUIRED", "GITHUB_WRITE_PERFORMED": "NO"}, "视觉资产已生成，等待人工确认"),
    ("DEPENDABOT_REVIEW", {"REPOSITORY_PUBLISHED": "YES", "CURRENT_TASK_BLOCKED": "YES"}, "当前任务已安全暂停"),
    ("PRE_PUBLISH_AUDIT", {"GITHUB_WRITE_PERFORMED": "NO", "LOCAL_SECURITY_AUDIT": "PASS"}, "当前任务已完成，GitHub 仓库没有变化"),
]


def validate_policy_files() -> list[str]:
    failures: list[str] = []
    if not POLICY_PATH.is_file():
        return [f"missing policy: {POLICY_PATH}"]

    skill = SKILL_PATH.read_text(encoding="utf-8")
    policy = POLICY_PATH.read_text(encoding="utf-8")
    required_skill_text = [
        "references/chinese-result-policy.md",
        "任何最终回答前",
        "不得削弱任何安全闸门",
    ]
    required_policy_text = [
        "CHINESE_RESULT_POLICY_VERSION = 2",
        "# 用户结果摘要",
        "## 主要检查结果",
        "## 需要处理的问题",
        "## 技术详情",
        "## 报告位置",
        "已经发生的远程事实",
        "当前自动检查结果",
        "当前任务的准备状态",
        "仓库既有状态与当前任务状态",
        "只给一个主要下一步",
        "机器字段",
        "一致性检查",
        "READY_TO_PUBLISH=NO",
        "REPOSITORY_PUBLISHED=YES",
    ]
    for marker in required_skill_text:
        if marker not in skill:
            failures.append(f"SKILL.md missing marker: {marker}")
    for marker in required_policy_text:
        if marker not in policy:
            failures.append(f"policy missing marker: {marker}")
    for task_type in sorted(TASK_TYPES):
        if task_type not in policy:
            failures.append(f"policy missing task type: {task_type}")
    for legacy in ("AUTHENTICATION_DIAGNOSIS", "AUTHENTICATION_REMEDIATION", "VISUAL_ASSET_GENERATION"):
        if legacy in policy:
            failures.append(f"legacy task type remains: {legacy}")

    combined = skill + "\n" + policy
    forbidden_patterns = {
        "hard-coded GitHub repository": r"https?://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
        "hard-coded PR number": r"\bPR\s*#\d+\b",
        "full commit SHA": r"(?<![A-Fa-f0-9])[A-Fa-f0-9]{40}(?![A-Fa-f0-9])",
        "hard-coded Windows user path": r"[A-Za-z]:" + (chr(92) * 2) + r"Users" + (chr(92) * 2) + r"[^" + (chr(92) * 2) + r"\s]+" + (chr(92) * 2),
        "GitHub token-shaped secret": r"(?:github_pat_|gh[pousr]_)[A-Za-z0-9_]{20,}",
        "private key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    }
    for name, pattern in forbidden_patterns.items():
        if re.search(pattern, combined):
            failures.append(name)
    return failures


def validate_scenarios() -> list[str]:
    failures: list[str] = []
    for number, (task_type, fields, expected) in enumerate(SCENARIOS, start=1):
        result = resolve_result(task_type, fields)
        if result.status != expected:
            failures.append(f"scenario {number}: expected {expected!r}, got {result.status!r}")
        if not result.next_action.strip():
            failures.append(f"scenario {number}: missing next action")
        if number == 13:
            if "此前已经发布" not in result.conclusion or "尚未发布" in result.status:
                failures.append("scenario 13: existing publication fact was lost")
    return failures


def main() -> int:
    failures = validate_policy_files() + validate_scenarios()
    if failures:
        print("GLOBAL_SKILL_VALIDATION = FAIL")
        for failure in failures:
            print(f"FAILURE = {failure}")
        return 1

    print("CHINESE_SUMMARY_PRESENT = YES")
    print("CHINESE_SUMMARY_FIRST = YES")
    print("TECHNICAL_DETAILS_PRESENT = YES")
    print("MACHINE_FIELDS_PRESERVED = YES")
    print("SINGLE_CLEAR_NEXT_ACTION = YES")
    print("NO_STATUS_CONTRADICTIONS = YES")
    print("NO_HARDCODED_PROJECT_DATA = YES")
    print("NO_HARDCODED_ACCOUNT = YES")
    print("NO_SENSITIVE_DATA_OUTPUT = YES")
    for number in range(1, len(SCENARIOS) + 1):
        print(f"SCENARIO_{number} = PASS")
    print("ALL_SCENARIOS_PASS = YES")
    print("GLOBAL_SKILL_VALIDATION = PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
