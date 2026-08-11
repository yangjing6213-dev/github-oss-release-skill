"""Conservative local fallback scan for secrets and private material.

This is intentionally a fallback, not a replacement for a history-aware
scanner such as Gitleaks.  Findings contain only masked, short previews.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

SECRET_PATTERNS: tuple[tuple[str, str, str], ...] = (
    ("private_key", r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----", "high"),
    ("github_token", r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b", "high"),
    ("aws_access_key", r"\bAKIA[0-9A-Z]{16}\b", "high"),
    ("jwt", r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b", "high"),
    ("secret_assignment", r"\b(?:api[_-]?key|access[_-]?key|auth[_-]?token|client[_-]?secret|password|passwd|secret|token)\b\s*[:=]\s*[\"']?([A-Za-z0-9_+/=.-]{8,})", "high"),
    ("connection_string", r"\b(?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[^\s\"']+", "high"),
)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_RE = re.compile(r"(?<!\d)(?:\+?86[ -]?)?1[3-9]\d{9}(?!\d)")
CN_ID_RE = re.compile(r"(?<!\d)\d{6}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[0-9Xx](?!\d)")
ABS_PATH_RE = re.compile(
    r"(?<![A-Za-z0-9])(?:"
    r"[A-Za-z]:\\(?=[A-Za-z0-9._~ -])[^\s\"'<>]+|"
    r"\\\\(?=[A-Za-z0-9._~ -])[^\s\"'<>]+|"
    r"/(?:Users|home|var/folders)/(?=[A-Za-z0-9._~ -])[^\s\"'<>]+"
    r")"
)
BROWSER_RE = re.compile(r"(?:AppData[\\/]Local[\\/](?:Google[\\/]Chrome|Microsoft[\\/]Edge)[\\/]User Data|(?:\.config[\\/]google-chrome|Firefox[\\/]Profiles))", re.IGNORECASE)
COOKIE_RE = re.compile(r"\b(?:cookie|session(?:id|_id)?|set-cookie)\b\s*[:=]\s*[^\s\"']+", re.IGNORECASE)

PLACEHOLDERS = {"replace-me", "replace_me", "your-token", "your_token", "example", "changeme", "change-me", "none", "null"}
SKIP_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tar", ".whl", ".exe", ".dll", ".so", ".pyc", ".mp4", ".mp3"}


def _mask(value: str) -> str:
    value = value.strip()
    if not value:
        return "[REDACTED]"
    # Keep at most two non-sensitive edge characters and never expose a full
    # token, email, phone number, or path.
    if len(value) <= 4:
        return "[REDACTED]"
    return f"{value[:2]}…{value[-1:]} [REDACTED]"


def _preview(line: str, match: re.Match[str] | None = None) -> str:
    if match:
        start, end = match.span()
        before = line[max(0, start - 12):start]
        after = line[end:end + 12]
        return (before + _mask(match.group(0)) + after).strip()[:80]
    return "[REDACTED]"


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _is_placeholder(value: str) -> bool:
    return value.strip(" \t\"'`<>()[]{}").lower() in PLACEHOLDERS


def _finding(path: str, line: int, kind: str, severity: str, preview: str) -> dict[str, Any]:
    return {
        "path": path,
        "line": line,
        "finding_type": kind,
        "severity": severity,
        "masked_preview": preview[:80],
    }


def _scan_file(path: Path, root: Path, max_bytes: int) -> list[dict[str, Any]]:
    shown = _display(path, root)
    findings: list[dict[str, Any]] = []
    name = path.name
    lower_name = name.lower()
    if (lower_name == ".env" or lower_name.startswith(".env.") and lower_name not in {".env.example", ".env.sample"}):
        findings.append(_finding(shown, 1, "env_file", "high", "[REDACTED_PATH]"))
    if any(part.lower() in {"cookies", "cookie", "sessions", "session"} for part in path.parts):
        findings.append(_finding(shown, 1, "cookie_session_path", "high", "[REDACTED_PATH]"))
    try:
        data = path.read_bytes()
    except OSError:
        return findings
    if len(data) > max_bytes or b"\x00" in data[:8192] or path.suffix.lower() in SKIP_SUFFIXES:
        return findings
    try:
        text = data.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return findings
    lines = text.splitlines() or [""]
    seen: set[tuple[int, str, str]] = set()
    for line_number, line in enumerate(lines, 1):
        def add(kind: str, severity: str, match: re.Match[str] | None) -> None:
            key = (line_number, kind, match.group(0) if match else "")
            if key in seen:
                return
            seen.add(key)
            findings.append(_finding(shown, line_number, kind, severity, _preview(line, match)))

        for kind, pattern, severity in SECRET_PATTERNS:
            for match in re.finditer(pattern, line, re.IGNORECASE):
                value = match.group(1) if match.lastindex else match.group(0)
                if kind == "secret_assignment" and _is_placeholder(value):
                    continue
                add(kind, severity, match)
        for match in COOKIE_RE.finditer(line):
            add("cookie_or_session_value", "high", match)
        for match in BROWSER_RE.finditer(line):
            add("browser_profile_path", "high", match)
        for match in ABS_PATH_RE.finditer(line):
            add("local_absolute_path", "medium", match)
        for match in PHONE_RE.finditer(line):
            add("phone_number", "high", match)
        for match in CN_ID_RE.finditer(line):
            add("identity_number", "high", match)
        for match in EMAIL_RE.finditer(line):
            email = match.group(0).lower()
            if email.endswith(("@example.com", "@example.org", "@example.net")):
                continue
            add("private_email", "medium", match)
    return sorted(findings, key=lambda item: (item["path"], item["line"], item["finding_type"], item["masked_preview"]))


def _collect(root: Path, paths: Iterable[str], include_git: bool) -> list[Path]:
    values = list(paths)
    if values:
        candidates = []
        for value in values:
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = root / path
            candidates.append(path.resolve())
    elif root.is_dir():
        candidates = list(root.rglob("*"))
    else:
        candidates = [root]
    result: list[Path] = []
    for path in candidates:
        if not path.is_file():
            continue
        if not include_git and ".git" in path.parts:
            continue
        result.append(path)
    return sorted(set(result), key=lambda item: str(item).casefold())


def scan(root_value: str | Path, paths: Iterable[str] = (), *, include_git: bool = False, max_bytes: int = 2_000_000, excludes: Iterable[str] = ()) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    excluded = {str(value).replace("\\", "/").strip("/") for value in excludes}
    findings: list[dict[str, Any]] = []
    scanned = 0
    for path in _collect(root, paths, include_git):
        shown = _display(path, root)
        if any(shown == item or shown.startswith(item + "/") for item in excluded):
            continue
        scanned += 1
        findings.extend(_scan_file(path, root, max_bytes))
    return {
        "root": str(root),
        "files_scanned": scanned,
        "finding_count": len(findings),
        "findings": findings,
        "valid": not findings,
        "scanner": "fallback",
        "github_write_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--include-git", action="store_true")
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = scan(args.root, args.paths, include_git=args.include_git, max_bytes=max(1, args.max_bytes), excludes=args.exclude)
    except Exception as exc:  # pragma: no cover
        result = {"valid": False, "error": type(exc).__name__, "findings": [], "github_write_performed": False}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True) if args.json else f"ERROR: {result['error']}")
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for finding in result["findings"]:
            print(f"{finding['path']}:{finding['line']}: {finding['finding_type']} ({finding['severity']}) {finding['masked_preview']}")
        print(f"SENSITIVE_CONTENT_VALID = {'YES' if result['valid'] else 'NO'}")
    return EXIT_OK if result["valid"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
