"""Read-only validator for Markdown badges and bilingual README parity."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


BADGE_RE = re.compile(r"\[!\[([^\]]*)\]\(([^)]+)\)\]\(([^)]+)\)")
GITHUB_RE = re.compile(r"github\.com[/:]([^/\s]+)/([^/#?\s]+)", re.IGNORECASE)
WORKFLOW_RE = re.compile(r"actions/workflows/([^/?#)]+)", re.IGNORECASE)
TOKEN_RE = re.compile(r"(?:token|access_token|api_key|apikey)=", re.IGNORECASE)
STATIC_RE = re.compile(r"img\.shields\.io/badge/[^)]*(?:passing|secure|coverage|maintained|production)", re.IGNORECASE)


def _assessment_module():
    path = Path(__file__).with_name("assess_badges.py")
    spec = importlib.util.spec_from_file_location("assess_badges", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _readme_badges(path: Path) -> list[dict[str, str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return []
    return [{"label": m.group(1), "BADGE_IMAGE_URL": m.group(2), "BADGE_TARGET_URL": m.group(3)} for m in BADGE_RE.finditer(text)]


def _signature(item: dict[str, str]) -> tuple[str, str]:
    return item["BADGE_IMAGE_URL"], item["BADGE_TARGET_URL"]


def _url_accessible(url: str) -> bool:
    try:
        request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "github-oss-release-badge-validator"})
        with urllib.request.urlopen(request, timeout=5) as response:
            return 200 <= int(response.status) < 400
    except (OSError, urllib.error.URLError, ValueError):
        return False


def validate(root_value: str | Path, owner: str, repository: str, default_branch: str = "main", *, check_urls: bool = False) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    readme = _readme_badges(root / "README.md")
    english = _readme_badges(root / "README.en.md")
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    duplicate_badges: list[dict[str, Any]] = []
    old_owner_badges: list[dict[str, Any]] = []
    url_accessibility: dict[str, bool | str] = {}
    seen: dict[tuple[str, str], int] = {}
    workflows = {path.name for path in (root / ".github" / "workflows").glob("*") if path.is_file() and path.suffix.lower() in {".yml", ".yaml"}} if (root / ".github" / "workflows").is_dir() else set()
    for index, item in enumerate(readme, 1):
        signature = _signature(item)
        if signature in seen:
            duplicate_badges.append({"index": index, "duplicate_of": seen[signature], **item})
        else:
            seen[signature] = index
        for field in ("BADGE_IMAGE_URL", "BADGE_TARGET_URL"):
            url = item[field]
            if not re.match(r"^https?://", url, re.IGNORECASE) or re.match(r"^[A-Za-z]:[/\\]", url):
                findings.append({"code": "invalid_badge_url", "field": field, "url": url})
            if TOKEN_RE.search(url):
                findings.append({"code": "token_query_parameter", "field": field})
            if check_urls and re.match(r"^https?://", url, re.IGNORECASE):
                url_accessibility[url] = _url_accessible(url)
                if not url_accessibility[url]:
                    findings.append({"code": "badge_url_not_accessible", "field": field, "url": url})
            elif re.match(r"^https?://", url, re.IGNORECASE):
                url_accessibility[url] = "NOT_CHECKED"
        accounts = [GITHUB_RE.search(item[field]) for field in ("BADGE_IMAGE_URL", "BADGE_TARGET_URL")]
        for match in accounts:
            if not match:
                continue
            actual_owner, actual_repo = match.group(1), match.group(2).removesuffix(".git")
            if actual_owner.lower() != owner.lower() or actual_repo.lower() != repository.lower():
                record = {"code": "old_owner_or_repository", "expected": f"{owner}/{repository}", "actual": f"{actual_owner}/{actual_repo}", **item}
                old_owner_badges.append(record)
                findings.append(record)
        workflow = WORKFLOW_RE.search(item["BADGE_IMAGE_URL"] + " " + item["BADGE_TARGET_URL"])
        if workflow and workflow.group(1) not in workflows:
            findings.append({"code": "workflow_file_missing", "workflow": workflow.group(1)})
        if STATIC_RE.search(item["BADGE_IMAGE_URL"]):
            findings.append({"code": "static_claim_badge", "url": item["BADGE_IMAGE_URL"]})
    if len(readme) > 6:
        warnings.append({"code": "badge_count_exceeds_recommendation", "count": len(readme), "maximum": 6})
    zh_signatures = {_signature(item) for item in readme}
    en_signatures = {_signature(item) for item in english}
    bilingual_match = zh_signatures == en_signatures
    if not bilingual_match:
        findings.append({"code": "bilingual_badges_mismatch", "README.md": sorted(zh_signatures), "README.en.md": sorted(en_signatures)})
    result = {
        "valid": not findings,
        "owner": owner,
        "repository": repository,
        "default_branch": default_branch,
        "badge_count": len(readme),
        "current_badges": readme,
        "duplicate_badges": duplicate_badges,
        "old_owner_badges": old_owner_badges,
        "bilingual_badges_match": bilingual_match,
        "findings": findings,
        "warnings": warnings,
        "url_accessibility": url_accessibility,
        "github_write_performed": False,
    }
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=Path.cwd())
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--default-branch", default="main")
    parser.add_argument("--check-urls", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    result = validate(args.project_root, args.owner, args.repository, args.default_branch, check_urls=args.check_urls)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    sys.exit(main())
