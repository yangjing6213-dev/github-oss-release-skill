"""Inspect distributable archives for secrets and local-only material."""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
ARCHIVE_SUFFIXES = (".whl", ".zip", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")
TEXT_SUFFIXES = {".md", ".txt", ".py", ".js", ".ts", ".json", ".toml", ".yaml", ".yml", ".cfg", ".ini", ".env", ".rs", ".go", ".xml", ".html", ".css", ".sh", ".ps1"}
RAW_DATA_SUFFIXES = {".csv", ".jsonl", ".parquet", ".pkl", ".pickle", ".sqlite", ".sqlite3", ".db", ".npy"}
VISUAL_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp", ".tif", ".tiff"}
LOCAL_REPORT_NAMES = {"PRE-PUBLISH-REPORT.md", "POST-PUBLISH-REPORT.md", "UPDATE-REPORT.md", "DEPENDABOT-REPORT.md"}
SECRET_RE = re.compile(
    r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----|\b(?:api[_-]?key|secret|token|password)\b\s*[:=]\s*[\"']?[A-Za-z0-9_+/=.-]{8,})",
    re.IGNORECASE,
)
ABS_PATH_RE = re.compile(r"(?:[A-Za-z]:\\[^\s\"'<>]+|/(?:Users|home|var)/[^\s\"'<>]+)")


def _mask(value: str) -> str:
    return "[REDACTED]" if len(value) < 5 else f"{value[:2]}…{value[-1:]} [REDACTED]"


def _finding(member: str, kind: str, severity: str, preview: str = "[REDACTED]") -> dict[str, str]:
    return {"member": member, "finding_type": kind, "severity": severity, "masked_preview": preview[:80]}


def _member_safe(name: str) -> tuple[bool, str]:
    normalized = name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or any(part == ".." for part in path.parts):
        return False, "unsafe_member_path"
    return True, normalized.lstrip("./")


def _member_findings(name: str, data: bytes, max_bytes: int) -> list[dict[str, str]]:
    safe, normalized = _member_safe(name)
    if not safe:
        return [_finding(name[:200], "unsafe_member_path", "high")]
    lower = normalized.lower()
    findings: list[dict[str, str]] = []
    path = PurePosixPath(normalized)
    if ".local-audit" in path.parts or ".local-backup" in path.parts:
        findings.append(_finding(normalized, "local_audit_or_backup", "high"))
    if path.name in LOCAL_REPORT_NAMES:
        findings.append(_finding(normalized, "local_only_report", "high"))
    if "backup" in lower or lower.endswith((".bak", ".orig", ".old")):
        findings.append(_finding(normalized, "backup_artifact", "high"))
    if any(marker in lower for marker in ("unfinished", "not_implemented", "wip")):
        findings.append(_finding(normalized, "unfinished_functionality", "high"))
    if path.suffix.lower() in RAW_DATA_SUFFIXES:
        findings.append(_finding(normalized, "raw_data", "high"))
    if path.suffix.lower() in VISUAL_SUFFIXES and any(
        marker in lower for marker in ("reference", "candidate", "draft", "source")
    ):
        findings.append(_finding(normalized, "excluded_visual_asset", "high"))
    if path.name.lower() in {".env", ".env.local", ".env.production", "cookies.sqlite", "cookies.json"}:
        findings.append(_finding(normalized, "secret_or_private_path", "high"))

    if len(data) <= max_bytes and (path.suffix.lower() in TEXT_SUFFIXES or b"\x00" not in data[:4096]):
        try:
            text = data.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            text = ""
        for line in text.splitlines():
            match = SECRET_RE.search(line)
            if match:
                findings.append(_finding(normalized, "secret_pattern", "high", _mask(match.group(0))))
            match = ABS_PATH_RE.search(line)
            if match:
                findings.append(_finding(normalized, "local_absolute_path", "medium", _mask(match.group(0))))
    return findings


def _archives(root: Path, values: Iterable[str]) -> list[Path]:
    supplied = list(values)
    if supplied:
        paths = []
        for value in supplied:
            path = Path(value).expanduser()
            if not path.is_absolute():
                path = root / path
            paths.append(path.resolve())
        return sorted({path for path in paths if path.is_file()}, key=lambda item: str(item).casefold())
    if not root.is_dir():
        return [root] if root.is_file() else []
    return sorted(
        {
            path.resolve()
            for path in root.rglob("*")
            if path.is_file() and path.name.lower().endswith(ARCHIVE_SUFFIXES) and ".git" not in path.parts
        },
        key=lambda item: str(item).casefold(),
    )


def _inspect_zip(path: Path, max_bytes: int) -> tuple[str, list[dict[str, str]], int]:
    findings: list[dict[str, str]] = []
    count = 0
    with zipfile.ZipFile(path) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            if info.is_dir():
                continue
            count += 1
            with archive.open(info) as stream:
                data = stream.read(max_bytes + 1)
            findings.extend(_member_findings(info.filename, data, max_bytes))
    return "wheel" if path.suffix.lower() == ".whl" else "zip", findings, count


def _inspect_tar(path: Path, max_bytes: int) -> tuple[str, list[dict[str, str]], int]:
    findings: list[dict[str, str]] = []
    count = 0
    with tarfile.open(path, mode="r:*") as archive:
        for member in sorted(archive.getmembers(), key=lambda item: item.name):
            if member.issym() or member.islnk():
                findings.append(_finding(member.name[:200], "link_member", "high"))
                continue
            if not member.isfile():
                continue
            count += 1
            stream = archive.extractfile(member)
            data = stream.read(max_bytes + 1) if stream else b""
            findings.extend(_member_findings(member.name, data, max_bytes))
    return "sdist" if path.name.lower().endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")) else "tar", findings, count


def inspect(root_value: str | Path, values: Iterable[str] = (), *, max_bytes: int = 2_000_000) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    artifacts: list[dict[str, Any]] = []
    for path in _archives(root, values):
        findings: list[dict[str, str]] = []
        artifact_format = "unknown"
        count = 0
        try:
            if path.name.lower().endswith((".whl", ".zip")):
                artifact_format, findings, count = _inspect_zip(path, max_bytes)
            elif path.name.lower().endswith((".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
                artifact_format, findings, count = _inspect_tar(path, max_bytes)
            else:
                findings.append(_finding(path.name, "unsupported_artifact_format", "medium"))
        except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
            findings.append(_finding(path.name, "unreadable_artifact", "high", type(exc).__name__))
        artifacts.append({"path": str(path), "format": artifact_format, "member_count": count, "findings": findings, "valid": not findings})
    all_findings = [finding for artifact in artifacts for finding in artifact["findings"]]
    return {
        "root": str(root),
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "finding_count": len(all_findings),
        "status": "NOT_CONFIGURED" if not artifacts else "PASS" if not all_findings else "FAIL",
        "valid": bool(artifacts) and not all_findings,
        "github_write_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("artifacts", nargs="*")
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = inspect(args.root, args.artifacts, max_bytes=max(1, args.max_bytes))
    except Exception as exc:  # pragma: no cover
        result = {"valid": False, "error": type(exc).__name__, "artifacts": [], "github_write_performed": False}
        print(json.dumps(result, ensure_ascii=False, sort_keys=True) if args.json else f"ERROR: {result['error']}")
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for artifact in result["artifacts"]:
            print(f"{artifact['path']}: {artifact['format']} ({'PASS' if artifact['valid'] else 'FAIL'})")
            for finding in artifact["findings"]:
                print(f"  {finding['member']}: {finding['finding_type']}")
        print(f"BUILD_ARTIFACTS_VALID = {'YES' if result['valid'] else 'NO'}")
    return EXIT_OK if result["valid"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
