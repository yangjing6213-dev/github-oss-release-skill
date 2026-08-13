"""Read-only, evidence-first badge assessment for a local project."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


BADGE_RE = re.compile(r"\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)")
GITHUB_RE = re.compile(r"github\.com[/:]([^/\s]+)/([^/#?\s]+)", re.IGNORECASE)
WORKFLOW_RE = re.compile(r"actions/workflows/([^/?#)]+)", re.IGNORECASE)
STATIC_CLAIM_RE = re.compile(r"(?:passing|secure|maintained|production[-_ ]?ready|coverage|quality)", re.IGNORECASE)
ORDER = ["CI", "Tests", "License", "Release", "Tag", "Package Version", "Python", "Node", "Supported Platform", "CodeQL", "Coverage", "Dependency Audit"]
QUALITY_SETUP = {
    "CI": "真实 CI Workflow 与成功运行记录",
    "CodeQL": "真实 CodeQL Workflow 与成功运行记录",
    "Coverage": "可验证覆盖率服务或公开端点",
    "Dependency Audit": "真实依赖审计 Workflow 与运行记录",
}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def _json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _badges(root: Path) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    for readme in (root / "README.md", root / "README.en.md"):
        text = _read(readme)
        for match in BADGE_RE.finditer(text):
            found.append(
                {
                    "readme": readme.name,
                    "label": match.group(1),
                    "BADGE_IMAGE_URL": match.group(2),
                    "BADGE_TARGET_URL": match.group(3),
                }
            )
    return found


def _workflow_files(root: Path) -> list[str]:
    directory = root / ".github" / "workflows"
    if not directory.is_dir():
        return []
    return sorted(path.name for path in directory.iterdir() if path.is_file() and path.suffix.lower() in {".yml", ".yaml"})


def _workflow_runs(metadata: dict[str, Any]) -> dict[str, bool]:
    result: dict[str, bool] = {}
    runs = metadata.get("workflow_runs", [])
    if not isinstance(runs, list):
        return result
    for run in runs:
        if not isinstance(run, dict):
            continue
        name = str(run.get("workflow") or run.get("name") or "")
        conclusion = str(run.get("conclusion") or run.get("status") or "").lower()
        if name:
            result[name] = result.get(name, False) or conclusion in {"success", "passed", "pass"}
    return result


def _version_evidence(root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    package = _json(root / "package.json")
    engines = package.get("engines") if isinstance(package.get("engines"), dict) else {}
    if engines and engines.get("node"):
        result["Node"] = str(engines["node"])
    if package.get("version"):
        result["Package Version"] = str(package["version"])
    pyproject = _read(root / "pyproject.toml")
    match = re.search(r"(?m)^\s*requires-python\s*=\s*[\"']([^\"']+)", pyproject)
    if match:
        result["Python"] = match.group(1)
    match = re.search(r"(?m)^\s*version\s*=\s*[\"']([^\"']+)", pyproject)
    if match:
        result["Package Version"] = match.group(1)
    cargo = _read(root / "Cargo.toml")
    match = re.search(r"(?m)^\s*version\s*=\s*[\"']([^\"']+)", cargo)
    if match:
        result["Package Version"] = match.group(1)
    skill = _read(root / "SKILL.md")
    match = re.search(r"SKILL_VERSION\s*=\s*(\d+\.\d+\.\d+)", skill)
    if match:
        result["Skill Version"] = match.group(1)
    return result


def _has_license(root: Path, metadata: dict[str, Any]) -> tuple[bool, str]:
    for name in ("LICENSE", "LICENSE.txt", "COPYING"):
        if (root / name).is_file():
            return True, name
    license_data = metadata.get("license")
    if isinstance(license_data, dict) and license_data.get("spdx_id"):
        return True, f"GitHub license metadata: {license_data['spdx_id']}"
    if isinstance(license_data, str) and license_data:
        return True, f"GitHub license metadata: {license_data}"
    return False, "no license file or verified metadata"


def _release_evidence(metadata: dict[str, Any]) -> tuple[bool, str]:
    release = metadata.get("release")
    if isinstance(release, dict) and (release.get("tag_name") or release.get("name")):
        return True, f"release={release.get('tag_name') or release.get('name')}"
    releases = metadata.get("releases")
    if isinstance(releases, list) and releases:
        return True, "release list is non-empty"
    return False, "no verified GitHub Release"


def _tag_evidence(metadata: dict[str, Any]) -> tuple[bool, str]:
    tags = metadata.get("tags")
    if isinstance(tags, list) and tags:
        return True, f"tags={len(tags)}"
    return False, "no verified Git tag"


def _coverage_evidence(metadata: dict[str, Any], current: list[dict[str, str]]) -> tuple[bool, str]:
    coverage = metadata.get("coverage")
    if isinstance(coverage, dict) and (coverage.get("url") or coverage.get("source")):
        return True, str(coverage.get("url") or coverage.get("source"))
    if isinstance(coverage, str) and coverage:
        return True, coverage
    for item in current:
        if re.search(r"codecov|coveralls|coverage", item["BADGE_IMAGE_URL"], re.IGNORECASE):
            if not STATIC_CLAIM_RE.search(item["BADGE_IMAGE_URL"]):
                return True, item["BADGE_IMAGE_URL"]
    return False, "no verifiable coverage service or endpoint"


def _account(url: str) -> tuple[str, str] | None:
    match = GITHUB_RE.search(url)
    return (match.group(1), match.group(2).removesuffix(".git")) if match else None


def _workflow_name(url: str) -> str | None:
    match = WORKFLOW_RE.search(url)
    return match.group(1) if match else None


def _candidate(name: str, category: str, owner: str, repository: str, branch: str, source: str, evidence: str) -> dict[str, Any]:
    path = f"{owner}/{repository}"
    if name == "CI" or name in {"CodeQL", "Dependency Audit"}:
        workflow = source
        return {
            "name": name,
            "category": category,
            "BADGE_EVIDENCE_STATUS": "VERIFIED_READY",
            "BADGE_IMAGE_URL": f"https://github.com/{path}/actions/workflows/{workflow}/badge.svg?branch={branch}",
            "BADGE_TARGET_URL": f"https://github.com/{path}/actions/workflows/{workflow}",
            "BADGE_SOURCE": source,
            "BADGE_EVIDENCE": evidence,
        }
    if name == "License":
        image = f"https://img.shields.io/github/license/{path}"
        target = f"https://github.com/{path}/blob/{branch}/LICENSE"
    elif name == "Release":
        image = f"https://img.shields.io/github/v/release/{path}"
        target = f"https://github.com/{path}/releases/latest"
    elif name == "Tag":
        image = f"https://img.shields.io/github/v/tag/{path}"
        target = f"https://github.com/{path}/tags"
    else:
        value = evidence.replace(" ", "%20")
        image = f"https://img.shields.io/badge/{name.lower().replace(' ', '-')}-{value}-informational"
        target = f"https://github.com/{path}"
    return {
        "name": name,
        "category": category,
        "BADGE_EVIDENCE_STATUS": "VERIFIED_READY",
        "BADGE_IMAGE_URL": image,
        "BADGE_TARGET_URL": target,
        "BADGE_SOURCE": source,
        "BADGE_EVIDENCE": evidence,
    }


def _classify_current(item: dict[str, str], owner: str, repository: str, workflows: list[str], runs: dict[str, bool], license_ok: bool, release_ok: bool, tag_ok: bool, coverage_ok: bool) -> dict[str, Any]:
    image = item["BADGE_IMAGE_URL"]
    target = item["BADGE_TARGET_URL"]
    text = f"{item['label']} {image} {target}"
    account = _account(image) or _account(target)
    result: dict[str, Any] = {
        **item,
        "BADGE_SOURCE": "README",
        "BADGE_EVIDENCE": "",
        "BADGE_EVIDENCE_STATUS": "NOT_RECOMMENDED",
    }
    if account and (account[0].lower() != owner.lower() or account[1].lower() != repository.lower()):
        result["BADGE_EVIDENCE_STATUS"] = "BLOCKED_INVALID_EVIDENCE"
        result["BADGE_EVIDENCE"] = "owner or repository does not match target"
        result["old_owner"] = account[0]
        return result
    if "actions/workflows/" in text.lower():
        workflow = _workflow_name(text)
        result["BADGE_SOURCE"] = workflow or "GitHub Actions"
        if workflow in workflows and runs.get(workflow, False):
            result["BADGE_EVIDENCE_STATUS"] = "VERIFIED_READY"
            result["BADGE_EVIDENCE"] = f"workflow={workflow}; successful run observed"
        else:
            result["BADGE_EVIDENCE_STATUS"] = "BLOCKED_INVALID_EVIDENCE"
            result["BADGE_EVIDENCE"] = "workflow file or successful run evidence missing"
        return result
    lower = text.lower()
    if "github/license" in lower or re.search(r"\blicense\b", item["label"], re.IGNORECASE):
        result["BADGE_SOURCE"] = "LICENSE or GitHub license metadata"
        result["BADGE_EVIDENCE_STATUS"] = "VERIFIED_READY" if license_ok else "BLOCKED_INVALID_EVIDENCE"
        result["BADGE_EVIDENCE"] = "license evidence found" if license_ok else "license evidence missing"
        return result
    if "github/v/release" in lower or "release" in item["label"].lower():
        result["BADGE_SOURCE"] = "GitHub Release"
        result["BADGE_EVIDENCE_STATUS"] = "VERIFIED_READY" if release_ok else "BLOCKED_INVALID_EVIDENCE"
        result["BADGE_EVIDENCE"] = "release evidence found" if release_ok else "release evidence missing"
        return result
    if "github/v/tag" in lower or "tag" in item["label"].lower():
        result["BADGE_SOURCE"] = "Git tag"
        result["BADGE_EVIDENCE_STATUS"] = "VERIFIED_READY" if tag_ok else "BLOCKED_INVALID_EVIDENCE"
        result["BADGE_EVIDENCE"] = "tag evidence found" if tag_ok else "tag evidence missing"
        return result
    if STATIC_CLAIM_RE.search(text):
        result["BADGE_EVIDENCE_STATUS"] = "BLOCKED_INVALID_EVIDENCE" if not coverage_ok or "coverage" in lower else "NOT_RECOMMENDED"
        result["BADGE_EVIDENCE"] = "static claim has no verifiable source"
        return result
    result["BADGE_EVIDENCE"] = "badge source is not recognized"
    return result


def assess(root_value: str | Path, owner: str, repository: str, default_branch: str = "main", *, metadata: dict[str, Any] | None = None, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    metadata = metadata or {}
    workflows = _workflow_files(root)
    runs = _workflow_runs(metadata)
    current = _badges(root)
    license_ok, license_source = _has_license(root, metadata)
    release_ok, release_source = _release_evidence(metadata)
    tag_ok, tag_source = _tag_evidence(metadata)
    coverage_ok, coverage_source = _coverage_evidence(metadata, current)

    classified = [_classify_current(item, owner, repository, workflows, runs, license_ok, release_ok, tag_ok, coverage_ok) for item in current]
    signatures: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for item in classified:
        signatures.setdefault((item["BADGE_IMAGE_URL"], item["BADGE_TARGET_URL"]), []).append(item)
    duplicate_badges = [items[0] for items in signatures.values() if len(items) > 1]
    broken = [item for item in classified if item["BADGE_EVIDENCE_STATUS"] == "BLOCKED_INVALID_EVIDENCE"]
    old_owner = [item for item in broken if item.get("old_owner")]
    not_recommended = [item for item in classified if item["BADGE_EVIDENCE_STATUS"] == "NOT_RECOMMENDED"]

    eligible: list[dict[str, Any]] = []
    setup: list[dict[str, str]] = []
    seen: set[str] = set()
    for workflow in workflows:
        lower = workflow.lower()
        if "codeql" in lower:
            name = "CodeQL"
        elif "audit" in lower or "dependabot" in lower or "security" in lower:
            name = "Dependency Audit"
        else:
            name = "CI"
        if runs.get(workflow, False):
            eligible.append(_candidate(name, "STATUS_BADGE", owner, repository, default_branch, workflow, f"workflow={workflow}; successful run observed"))
        elif name not in {item["name"] for item in setup}:
            setup.append({"name": name, "BADGE_EVIDENCE_STATUS": "REQUIRES_QUALITY_SETUP", "BADGE_EVIDENCE": QUALITY_SETUP[name]})
    if not workflows:
        setup.append({"name": "CI", "BADGE_EVIDENCE_STATUS": "REQUIRES_QUALITY_SETUP", "BADGE_EVIDENCE": QUALITY_SETUP["CI"]})
    if license_ok:
        eligible.append(_candidate("License", "METADATA_BADGE", owner, repository, default_branch, license_source, license_source))
    if release_ok:
        eligible.append(_candidate("Release", "METADATA_BADGE", owner, repository, default_branch, "GitHub Release", release_source))
    elif tag_ok:
        eligible.append(_candidate("Tag", "METADATA_BADGE", owner, repository, default_branch, "Git tag", tag_source))
    versions = _version_evidence(root)
    for name in ("Package Version", "Python", "Node", "Skill Version"):
        if versions.get(name):
            eligible.append(_candidate(name, "METADATA_BADGE", owner, repository, default_branch, name, versions[name]))
    if coverage_ok:
        eligible.append(_candidate("Coverage", "STATUS_BADGE", owner, repository, default_branch, "coverage service", coverage_source))
    else:
        setup.append({"name": "Coverage", "BADGE_EVIDENCE_STATUS": "REQUIRES_QUALITY_SETUP", "BADGE_EVIDENCE": QUALITY_SETUP["Coverage"]})
    if not any(item["name"] == "CodeQL" for item in eligible) and not any(item["name"] == "CodeQL" for item in setup):
        setup.append({"name": "CodeQL", "BADGE_EVIDENCE_STATUS": "REQUIRES_QUALITY_SETUP", "BADGE_EVIDENCE": QUALITY_SETUP["CodeQL"]})
    if not any(item["name"] == "Dependency Audit" for item in eligible) and not any(item["name"] == "Dependency Audit" for item in setup):
        setup.append({"name": "Dependency Audit", "BADGE_EVIDENCE_STATUS": "REQUIRES_QUALITY_SETUP", "BADGE_EVIDENCE": QUALITY_SETUP["Dependency Audit"]})

    # Keep one source per meaning and cap the default README recommendation.
    by_name = {item["name"]: item for item in eligible}
    recommended = [name for name in ORDER if name in by_name][:6]
    visibility = str(metadata.get("visibility", "unknown")).lower()
    result = {
        "project_name": root.name,
        "owner": owner,
        "repository": repository,
        "default_branch": default_branch,
        "current_badges": classified,
        "eligible_badges": [by_name[name] for name in recommended],
        "badges_requiring_setup": setup,
        "not_applicable_badges": [name for name in ("Python", "Node", "Supported Platform") if name not in versions],
        "not_recommended_badges": not_recommended,
        "broken_badges": broken,
        "old_owner_badges": old_owner,
        "duplicate_badges": duplicate_badges,
        "recommended_badge_order": recommended,
        "recommended_badge_count": len(recommended),
        "simplification_advice": (len(eligible) > 6 or len(current) > 6),
        "quality_gates_recommended": setup,
        "visibility": visibility,
        "manifest_received": manifest is not None,
        "github_write_performed": False,
        "writes_performed": False,
    }
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=Path.cwd())
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--default-branch", default="main")
    parser.add_argument("--metadata-json", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    metadata = _json(args.metadata_json) if args.metadata_json else {}
    manifest = _json(args.manifest) if args.manifest else None
    result = assess(args.project_root, args.owner, args.repository, args.default_branch, metadata=metadata, manifest=manifest)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
