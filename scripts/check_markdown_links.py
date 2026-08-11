"""Check local Markdown links and image paths without network access by default."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
LOCAL_ONLY_NAMES = {
    "PRE-PUBLISH-REPORT.md",
    "POST-PUBLISH-REPORT.md",
    "UPDATE-REPORT.md",
    "DEPENDABOT-REPORT.md",
}
LOCAL_ONLY_PARTS = {".local-audit", ".local-backup"}
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel", "data", "ftp", "irc"}

INLINE_RE = re.compile(
    r"(?P<image>!)?\[[^\]]*\]\(\s*(?:<(?P<bracket>[^>]+)>|(?P<bare>[^\s)]+))[^)]*\)",
    re.IGNORECASE,
)
REFERENCE_RE = re.compile(r"^\s*\[[^\]]+\]:\s*(?:<([^>]+)>|(\S+))", re.IGNORECASE)
HTML_RE = re.compile(r"<(?:a\s+[^>]*href|img\s+[^>]*src)\s*=\s*[\"']([^\"']+)", re.IGNORECASE)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)(?:\s+#+\s*)?$")
ID_RE = re.compile(r"\bid\s*=\s*[\"']([^\"']+)", re.IGNORECASE)


def _is_local_only(value: str) -> bool:
    path = PurePosixPath(value.replace("\\", "/"))
    return bool(set(path.parts) & LOCAL_ONLY_PARTS) or path.name in LOCAL_ONLY_NAMES


def _slug(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value).strip().lower()
    value = re.sub(r"[^\w\- ]+", "", value, flags=re.UNICODE)
    return re.sub(r"[\s\-]+", "-", value).strip("-")


def _safe_target(target: str) -> str:
    target = html.unescape(target.strip())
    if target.startswith("<") and target.endswith(">"):  # defensive
        target = target[1:-1]
    return target


def _extract(lines: list[str]) -> list[tuple[int, str, str]]:
    links: list[tuple[int, str, str]] = []
    fenced = False
    for number, line in enumerate(lines, 1):
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            continue
        if fenced:
            continue
        occupied: list[tuple[int, int]] = []
        for match in INLINE_RE.finditer(line):
            target = match.group("bracket") or match.group("bare")
            if target:
                links.append((number, _safe_target(target), "image" if match.group("image") else "link"))
                occupied.append(match.span())
        for match in HTML_RE.finditer(line):
            target = _safe_target(match.group(1))
            if target:
                links.append((number, target, "html"))
        match = REFERENCE_RE.match(line)
        if match:
            target = match.group(1) or match.group(2)
            if target:
                links.append((number, _safe_target(target), "reference"))
    return links


def _visible_lines(lines: list[str]) -> list[str]:
    visible: list[str] = []
    fenced = False
    for line in lines:
        if re.match(r"^\s*(```|~~~)", line):
            fenced = not fenced
            visible.append("")
        else:
            visible.append("" if fenced else line)
    return visible


def _findings_for_file(path: Path, root: Path, allow_network: bool) -> tuple[list[dict[str, Any]], int, int]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [{"path": path.name, "line": 1, "target": "", "finding_type": "unreadable", "severity": "high", "reason": type(exc).__name__}], 0, 0
    lines = text.splitlines()
    visible_lines = _visible_lines(lines)
    headings = {_slug(match.group(1)) for line in visible_lines if (match := HEADING_RE.match(line))}
    headings.update(match.group(1) for match in ID_RE.finditer(text))
    findings: list[dict[str, Any]] = []
    checked = 0
    external_skipped = 0
    try:
        shown_source = path.relative_to(root).as_posix()
    except ValueError:
        shown_source = path.name
    for line_number, raw_target, link_type in _extract(lines):
        target = _safe_target(raw_target)
        parsed = urllib.parse.urlsplit(target)
        scheme = parsed.scheme.lower()
        if scheme in EXTERNAL_SCHEMES or target.startswith("//"):
            if not allow_network:
                external_skipped += 1
                continue
            try:
                request = urllib.request.Request(target, method="HEAD")
                with urllib.request.urlopen(request, timeout=5) as response:  # read-only
                    if getattr(response, "status", 200) >= 400:
                        raise OSError(f"http_{response.status}")
            except Exception as exc:  # network is explicitly opt-in and best effort
                findings.append({"path": shown_source, "line": line_number, "target": target[:200], "finding_type": "external_unreachable", "severity": "medium", "reason": type(exc).__name__})
            continue
        checked += 1
        fragment = urllib.parse.unquote(parsed.fragment)
        file_part = urllib.parse.unquote(parsed.path)
        if not file_part:
            if fragment and fragment not in headings and _slug(fragment) not in headings:
                findings.append({"path": shown_source, "line": line_number, "target": target[:200], "finding_type": "missing_anchor", "severity": "medium"})
            continue
        windows = PureWindowsPath(file_part)
        posix = PurePosixPath(file_part)
        if posix.is_absolute() or windows.is_absolute() or windows.drive:
            findings.append({"path": shown_source, "line": line_number, "target": target[:200], "finding_type": "absolute_path", "severity": "high"})
            continue
        candidate = (path.parent / Path(*posix.parts)).resolve()
        try:
            relative = candidate.relative_to(root).as_posix()
        except ValueError:
            findings.append({"path": shown_source, "line": line_number, "target": target[:200], "finding_type": "path_escape", "severity": "high"})
            continue
        if _is_local_only(relative):
            findings.append({"path": shown_source, "line": line_number, "target": target[:200], "finding_type": "local_only_reference", "severity": "high"})
            continue
        if not candidate.exists():
            findings.append({"path": shown_source, "line": line_number, "target": target[:200], "finding_type": "missing_target", "severity": "high"})
            continue
        if fragment and candidate.is_file() and candidate.suffix.lower() in {".md", ".markdown"}:
            try:
                target_text = candidate.read_text(encoding="utf-8")
                target_anchors = {_slug(m.group(1)) for line in target_text.splitlines() if (m := HEADING_RE.match(line))}
                target_anchors.update(m.group(1) for m in ID_RE.finditer(target_text))
            except (OSError, UnicodeError):
                target_anchors = set()
            if fragment not in target_anchors and _slug(fragment) not in target_anchors:
                findings.append({"path": shown_source, "line": line_number, "target": target[:200], "finding_type": "missing_anchor", "severity": "medium"})
    return findings, checked, external_skipped


def check(root_value: str | Path, files: Iterable[str | Path] = (), *, allow_network: bool = False) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    paths: list[Path] = []
    supplied = list(files)
    if supplied:
        for value in supplied:
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = root / path
            paths.append(path.resolve())
    elif root.is_dir():
        paths = sorted(
            (path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in {".md", ".markdown"} and ".git" not in path.parts),
            key=lambda item: str(item).casefold(),
        )
    elif root.is_file():
        paths = [root]

    findings: list[dict[str, Any]] = []
    checked = 0
    external_skipped = 0
    for path in paths:
        file_findings, local_checked, skipped = _findings_for_file(path, root if root.is_dir() else path.parent, allow_network)
        findings.extend(file_findings)
        checked += local_checked
        external_skipped += skipped
    return {
        "root": str(root),
        "files_scanned": len(paths),
        "links_checked": checked,
        "external_skipped": external_skipped,
        "network_mode": "readonly" if allow_network else "disabled",
        "findings": findings,
        "status": "NOT_CONFIGURED" if not paths else "PASS" if not findings else "FAIL",
        "valid": bool(paths) and not findings,
        "github_write_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("files", nargs="*")
    parser.add_argument("--allow-network", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = check(args.root, args.files, allow_network=args.allow_network)
    except Exception as exc:  # pragma: no cover
        result = {"valid": False, "error": type(exc).__name__, "github_write_performed": False}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True) if args.json else f"ERROR: {result['error']}")
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for finding in result["findings"]:
            print(f"{finding.get('path')}:{finding.get('line')}: {finding.get('finding_type')}")
        print(f"MARKDOWN_LINKS_VALID = {'YES' if result['valid'] else 'NO'}")
    return EXIT_OK if result["valid"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
