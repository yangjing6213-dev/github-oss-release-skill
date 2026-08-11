"""Validate strict UTF-8 for files or a release manifest.

Conversion is opt-in.  It requires an explicit source encoding or a reliable
Unicode BOM, writes a byte-for-byte backup first, and never changes decoded
Unicode text, line endings, or layout.
"""

from __future__ import annotations

import argparse
import codecs
import hashlib
import json
import shutil
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

BINARY_SUFFIXES = {
    ".7z", ".avi", ".bmp", ".class", ".dll", ".doc", ".docx", ".exe",
    ".gif", ".gz", ".ico", ".jar", ".jpeg", ".jpg", ".mov", ".mp3",
    ".mp4", ".o", ".obj", ".pdf", ".png", ".pyc", ".so", ".tar",
    ".ttf", ".webm", ".webp", ".whl", ".woff", ".woff2", ".xls",
    ".xlsx", ".xz", ".zip",
}


def _binary(data: bytes, path: Path) -> bool:
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    if not data:
        return False
    sample = data[:8192]
    if b"\x00" in sample:
        # UTF-16 BOM is reliable text evidence, not a binary marker.
        return not sample.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
    control = sum(byte < 9 or 13 < byte < 32 for byte in sample)
    return control / len(sample) > 0.20


def _manifest_paths(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if isinstance(value, list):
        return [str(item.get("path") if isinstance(item, dict) else item) for item in value]
    if isinstance(value, dict):
        values = value.get("files", value.get("entries", []))
        if not isinstance(values, list):
            raise ValueError("manifest_files_must_be_a_list")
        return [str(item.get("path") if isinstance(item, dict) else item) for item in values]
    raise ValueError("manifest_must_be_a_list_or_object")


def _safe_manifest_path(root: Path, value: str) -> Path:
    posix = PurePosixPath(value.replace("\\", "/"))
    windows = PureWindowsPath(value)
    if posix.is_absolute() or windows.is_absolute() or windows.drive or ".." in posix.parts:
        raise ValueError("unsafe_manifest_path")
    candidate = (root / Path(*posix.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("manifest_path_escape") from exc
    return candidate


def _collect(paths: Iterable[Path]) -> list[Path]:
    files: set[Path] = set()
    for path in paths:
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and ".git" not in child.parts:
                    files.add(child.resolve())
        else:
            files.add(path.resolve())
    return sorted(files, key=lambda item: str(item).casefold())


def _display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def _source_encoding(data: bytes, requested: str | None) -> str | None:
    if requested:
        return requested
    if data.startswith(codecs.BOM_UTF8):
        return "utf-8-sig"
    if data.startswith(codecs.BOM_UTF16_LE) or data.startswith(codecs.BOM_UTF16_BE):
        return "utf-16"
    if data.startswith(codecs.BOM_UTF32_LE) or data.startswith(codecs.BOM_UTF32_BE):
        return "utf-32"
    return None


def validate(
    files: Iterable[Path],
    *,
    root: Path,
    convert: bool = False,
    encoding: str | None = None,
    backup_dir: Path | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    checked: list[str] = []
    binary: list[str] = []
    invalid: list[dict[str, str]] = []
    converted: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []

    for path in _collect(files):
        shown = _display(path, root)
        if not path.is_file():
            errors.append({"path": shown, "reason": "missing"})
            continue
        try:
            data = path.read_bytes()
        except OSError as exc:
            errors.append({"path": shown, "reason": type(exc).__name__})
            continue
        if _binary(data, path):
            binary.append(shown)
            continue
        checked.append(shown)
        try:
            data.decode("utf-8", errors="strict")
            continue
        except UnicodeDecodeError as exc:
            decode_error = f"invalid_utf8_at_byte_{exc.start}"

        if not convert:
            invalid.append({"path": shown, "reason": decode_error})
            continue
        source = _source_encoding(data, encoding)
        if not source:
            invalid.append({"path": shown, "reason": "source_encoding_required"})
            continue
        try:
            text = data.decode(source, errors="strict")
            utf8 = text.encode("utf-8")
            if utf8.decode("utf-8", errors="strict") != text:
                raise UnicodeError("unicode_roundtrip_failed")
        except (LookupError, UnicodeError) as exc:
            invalid.append({"path": shown, "reason": type(exc).__name__})
            continue

        destination = backup_dir or (root / ".utf8-backup")
        try:
            relative = path.relative_to(root)
        except ValueError:
            digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()[:12]
            relative = Path(f"{digest}-{path.name}")
        backup = (destination / relative).resolve()
        try:
            backup.parent.mkdir(parents=True, exist_ok=True)
            if backup.exists():
                raise FileExistsError("backup_exists")
            shutil.copy2(path, backup)
            path.write_bytes(utf8)
        except OSError as exc:
            errors.append({"path": shown, "reason": type(exc).__name__})
            continue
        converted.append({"path": shown, "backup": _display(backup, root), "source_encoding": source})

    return {
        "checked": sorted(checked),
        "binary_skipped": sorted(binary),
        "invalid": invalid,
        "converted": converted,
        "errors": errors,
        "status": "NOT_CONFIGURED" if not checked and not binary and not converted and not invalid and not errors else "PASS" if not invalid and not errors else "FAIL",
        "valid": bool(checked or binary or converted) and not invalid and not errors,
        "files_modified": len(converted),
        "github_write_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--root", default=".")
    parser.add_argument("--manifest")
    parser.add_argument("--convert", action="store_true")
    parser.add_argument("--encoding", help="explicit source encoding for conversion")
    parser.add_argument("--backup-dir")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    paths = [Path(value).expanduser().resolve() for value in args.paths]
    try:
        if args.manifest:
            manifest = Path(args.manifest).expanduser().resolve()
            paths.extend(_safe_manifest_path(root, item) for item in _manifest_paths(manifest))
        if not paths:
            paths = [root]
        result = validate(
            paths,
            root=root,
            convert=args.convert,
            encoding=args.encoding,
            backup_dir=Path(args.backup_dir).expanduser().resolve() if args.backup_dir else None,
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "valid": False,
            "error": type(exc).__name__,
            "files_modified": 0,
            "github_write_performed": False,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) if args.json else f"ERROR: {result['error']}")
        return EXIT_USAGE

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for finding in result["invalid"]:
            print(f"{finding['path']}: {finding['reason']}")
        for finding in result["errors"]:
            print(f"{finding['path']}: {finding['reason']}")
        print(f"UTF8_VALID = {'YES' if result['valid'] else 'NO'}")
    return EXIT_OK if result["valid"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
