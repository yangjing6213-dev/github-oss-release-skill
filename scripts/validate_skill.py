"""Validate the structure and safety invariants of a github-oss-release Skill."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
EXPECTED_SCRIPTS = (
    "inspect_auth.py",
    "inspect_repository.py",
    "build_release_manifest.py",
    "validate_utf8.py",
    "check_markdown_links.py",
    "scan_sensitive_content.py",
    "inspect_build_artifacts.py",
    "validate_skill.py",
    "run_scenario_tests.py",
)
EXPECTED_TEMPLATES = (
    "PRE-PUBLISH-REPORT.md",
    "POST-PUBLISH-REPORT.md",
    "UPDATE-REPORT.md",
    "DEPENDABOT-REPORT.md",
    "LEGACY-WORKSPACE-DO-NOT-PUSH.md",
)
APPROVAL_WORDS = {
    "APPROVE_GITHUB_PUBLISH",
    "APPROVE_GITHUB_PR_MERGE",
    "APPROVE_GITHUB_RELEASE",
    "APPROVE_GIT_HISTORY_REMEDIATION",
    "APPROVE_REMOTE_DESTRUCTIVE_CHANGE",
}
SECRET_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----)",
    re.IGNORECASE,
)
ABS_PATH_RE = re.compile(r"(?<![A-Za-z0-9])(?:[A-Za-z]:\\[A-Za-z0-9_.-]+(?:\\[^\s\"'<>]+)+|/(?:Users|home)/[A-Za-z0-9_.-]+(?:/[^\s\"'<>]+)+)")
GITHUB_ACCOUNT_RE = re.compile(r"(?:https?://|git@)github\.com[/:]([^/\s]+)/([^\s/#]+)", re.IGNORECASE)
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter(text: str) -> tuple[dict[str, str], list[str]]:
    errors: list[str] = []
    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return {}, ["frontmatter_missing"]
    lines = text.splitlines()
    try:
        end = lines[1:].index("---") + 1
    except ValueError:
        return {}, ["frontmatter_unclosed"]
    values: dict[str, str] = {}
    for line in lines[1:end]:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            errors.append("frontmatter_invalid_line")
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip("\"'")
    return values, errors


def _yaml_check(path: Path) -> str | None:
    try:
        text = _read(path)
    except (OSError, UnicodeError) as exc:
        return type(exc).__name__
    try:
        import yaml  # type: ignore

        yaml.safe_load(text)
        return None
    except ImportError:
        # Small dependency-free fallback: reject tabs, malformed indentation,
        # and lines that cannot be a basic YAML mapping/list/comment.
        for line in text.splitlines():
            if "\t" in line or (line.strip() and not line.startswith((" ", "-", "#")) and ":" not in line):
                return "yaml_parser_unavailable_or_basic_syntax_error"
        return None
    except Exception as exc:
        return type(exc).__name__


def _iter_text_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item).casefold()):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            data = path.read_bytes()
        except OSError:
            continue
        if b"\x00" in data[:8192]:
            continue
        files.append(path)
    return files


def _safety_findings(root: Path, project_name: str | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for path in _iter_text_files(root):
        try:
            text = _read(path)
        except (OSError, UnicodeError):
            continue
        shown = path.relative_to(root).as_posix()
        for line_number, line in enumerate(text.splitlines(), 1):
            if SECRET_RE.search(line):
                findings.append({"path": shown, "line": line_number, "finding_type": "secret_pattern"})
            # Ignore generic regex/source examples and the documented fallback
            # path placeholder; only concrete user paths count.
            for match in ABS_PATH_RE.finditer(line):
                value = match.group(0)
                if ".codex/skills/github-oss-release" in value.replace("\\", "/"):
                    continue
                findings.append({"path": shown, "line": line_number, "finding_type": "hardcoded_absolute_path"})
            for match in GITHUB_ACCOUNT_RE.finditer(line):
                owner = match.group(1).strip("<>{}[]")
                repository = match.group(2).strip("<>{}[]")
                if owner.lower() in {"owner", "org", "user", "username", "example"} or repository.lower() in {"repo", "repository", "project", "example"}:
                    continue
                findings.append({"path": shown, "line": line_number, "finding_type": "hardcoded_github_account"})
            if project_name and project_name.lower() not in {"github-oss-release", root.name.lower()} and project_name.lower() in line.lower():
                findings.append({"path": shown, "line": line_number, "finding_type": "hardcoded_project_name"})
    # Deduplicate repeated rule matches while retaining deterministic order.
    return sorted({(item["path"], item["line"], item["finding_type"]): item for item in findings}.values(), key=lambda item: (item["path"], item["line"], item["finding_type"]))


def validate(root_value: str | Path, *, project_name: str | None = None) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    errors: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}
    skill = root / "SKILL.md"
    if not root.is_dir():
        return {"skill_root": str(root), "valid": False, "errors": [{"code": "skill_root_missing"}], "github_write_performed": False}

    try:
        text = _read(skill)
        checks["utf8"] = True
    except (OSError, UnicodeError) as exc:
        text = ""
        checks["utf8"] = False
        errors.append({"code": "skill_utf8", "detail": type(exc).__name__})
    word_count = len(re.findall(r"\S+", text))
    checks["skill_word_count"] = word_count <= 800
    if word_count > 800:
        errors.append({"code": "skill_too_long", "words": word_count})
    front, front_errors = _frontmatter(text)
    for error in front_errors:
        errors.append({"code": error})
    name = front.get("name", "")
    description = front.get("description", "")
    if not NAME_RE.fullmatch(name):
        errors.append({"code": "name_format"})
    if not description.startswith("Use when"):
        errors.append({"code": "description_prefix"})
    if len(re.findall(r"(?:→|->|git\s+(?:push|commit)|APPROVE_)", description, re.IGNORECASE)) >= 3:
        errors.append({"code": "description_contains_workflow"})
    checks["frontmatter"] = not front_errors and bool(name) and bool(description)

    # Links in SKILL.md are local evidence links; external links do not need a
    # network check here.
    links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", text)
    for target in links:
        target = target.strip().split("#", 1)[0].strip("<>")
        if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("//"):
            continue
        target_path = (skill.parent / target.replace("\\", "/")).resolve()
        if not target_path.exists():
            errors.append({"code": "reference_missing", "path": target})
    checks["references"] = not any(item["code"] == "reference_missing" for item in errors)

    missing_scripts = [name for name in EXPECTED_SCRIPTS if not (root / "scripts" / name).is_file()]
    missing_templates = [name for name in EXPECTED_TEMPLATES if not (root / "templates" / name).is_file()]
    for item in missing_scripts:
        errors.append({"code": "script_missing", "path": item})
    for item in missing_templates:
        errors.append({"code": "template_missing", "path": item})
    checks["scripts"] = not missing_scripts
    checks["templates"] = not missing_templates

    text_encoding_errors: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*"), key=lambda item: str(item).casefold()):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            text_encoding_errors.append({"code": "file_read", "path": path.relative_to(root).as_posix(), "detail": type(exc).__name__})
            continue
        if b"\x00" in data[:8192]:
            continue
        try:
            data.decode("utf-8", errors="strict")
        except UnicodeDecodeError as exc:
            text_encoding_errors.append({"code": "file_utf8", "path": path.relative_to(root).as_posix(), "detail": f"byte_{exc.start}"})
    errors.extend(text_encoding_errors)
    checks["all_text_utf8"] = not text_encoding_errors

    yaml_path = root / "agents" / "openai.yaml"
    yaml_error = _yaml_check(yaml_path) if yaml_path.exists() else "yaml_missing"
    if yaml_error:
        errors.append({"code": "yaml_invalid", "detail": yaml_error})
    checks["yaml"] = yaml_error is None

    safety = _safety_findings(root, project_name)
    errors.extend(safety)
    checks["no_hardcoded_project_data"] = not any(item["finding_type"] == "hardcoded_project_name" for item in safety)
    checks["no_hardcoded_account"] = not any(item["finding_type"] == "hardcoded_github_account" for item in safety)
    checks["no_secret"] = not any(item["finding_type"] == "secret_pattern" for item in safety)
    checks["no_absolute_path"] = not any(item["finding_type"] == "hardcoded_absolute_path" for item in safety)

    all_text = "\n".join(_read(path) for path in _iter_text_files(root) if path != skill)
    policy = root / "references" / "chinese-result-policy.md"
    checks["chinese_result_policy"] = policy.is_file() and "# 用户结果摘要" in _read(policy) if policy.exists() else False
    if not checks["chinese_result_policy"]:
        errors.append({"code": "chinese_result_policy_missing"})
    missing_approval_words = sorted(word for word in APPROVAL_WORDS if word not in (text + "\n" + all_text))
    if missing_approval_words:
        errors.append({"code": "authorization_words_missing", "missing": missing_approval_words})
    # A safety policy must contain the prohibition alongside any mention of a
    # dangerous operation; this catches accidental contradictory edits without
    # trying to understand every prose sentence.
    lower = (text + "\n" + all_text).lower()
    if ("force-push" in lower or "force push" in lower) and not any(token in lower for token in ("never", "prohibited", "禁止", "不得")):
        errors.append({"code": "contradictory_force_push_rule"})
    checks["authorization_consistency"] = not any(item.get("code") == "authorization_words_missing" for item in errors)

    return {
        "skill_root": str(root),
        "skill_name": name or None,
        "skill_version": "2.0.0" if "2.0.0" in text else None,
        "checks": checks,
        "errors": errors,
        "valid": not errors,
        "github_write_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_root", nargs="?", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--project-name")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = validate(args.skill_root, project_name=args.project_name)
    except Exception as exc:  # pragma: no cover
        result = {"valid": False, "error": type(exc).__name__, "errors": [], "github_write_performed": False}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True) if args.json else f"ERROR: {result['error']}")
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for error in result["errors"]:
            print(f"{error.get('code')}: {error.get('path', error.get('detail', ''))}")
        print(f"SKILL_VALID = {'YES' if result['valid'] else 'NO'}")
    return EXIT_OK if result["valid"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
