"""Build an exact, read-only public file manifest for a project."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import sys
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
WILDCARD_CHARS = set("*?[")


def _posix(value: str) -> str:
    return value.replace("\\", "/").strip()


def _validate_rule(value: str) -> tuple[str | None, str | None]:
    raw = _posix(value)
    if "\x00" in raw:
        return None, "nul_in_rule"
    if not raw or raw == ".":
        return ".", None
    windows = PureWindowsPath(raw)
    posix = PurePosixPath(raw)
    if windows.is_absolute() or posix.is_absolute() or windows.drive:
        return None, "absolute_path_rule"
    if any(part == ".." for part in posix.parts):
        return None, "path_escape_rule"
    return raw[2:] if raw.startswith("./") else raw, None


def _read_rules(path: Path) -> tuple[list[str], list[str]]:
    """Read a newline list or a small JSON {include/exclude/files} object."""
    text = path.read_text(encoding="utf-8")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return [line.strip() for line in text.splitlines() if line.strip() and not line.lstrip().startswith("#")], []
    if isinstance(value, list):
        return [str(item) for item in value], []
    if isinstance(value, dict):
        includes = value.get("include", value.get("files", []))
        excludes = value.get("exclude", [])
        if isinstance(includes, str):
            includes = [includes]
        if isinstance(excludes, str):
            excludes = [excludes]
        return [str(item) for item in includes or []], [str(item) for item in excludes or []]
    raise ValueError("rule_file_must_be_list_or_object")


def _is_local_only(relative: str) -> bool:
    path = PurePosixPath(relative)
    # Reports are local-only only when instantiated at the project root.
    # Publishable templates under ``templates/`` must remain eligible.
    return bool(set(path.parts) & LOCAL_ONLY_PARTS) or (
        len(path.parts) == 1 and path.name in LOCAL_ONLY_NAMES
    )


def _matches(path: str, pattern: str) -> bool:
    # fnmatch handles ** consistently on Windows once paths are normalized.
    normalized = pattern[2:] if pattern.startswith("./") else pattern
    return fnmatch.fnmatchcase(path, normalized) or PurePosixPath(path).match(normalized)


def _all_files(root: Path) -> list[str]:
    result: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts or path.suffix.lower() == ".pyc":
            continue
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            continue
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            continue
        result.append(relative)
    return sorted(result)


def _expand(root: Path, rule: str) -> tuple[list[str], bool]:
    has_wildcard = bool(WILDCARD_CHARS & set(rule))
    candidate = root / Path(rule)
    paths: list[Path]
    if has_wildcard:
        paths = list(root.glob(rule))
    elif candidate.is_dir():
        paths = list(candidate.rglob("*"))
    elif candidate.exists():
        paths = [candidate]
    else:
        paths = []
    values: list[str] = []
    for path in paths:
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts or path.suffix.lower() == ".pyc":
            continue
        try:
            path.resolve().relative_to(root.resolve())
        except ValueError:
            # A symlink/glob target escaping the project is never publishable.
            continue
        try:
            values.append(path.relative_to(root).as_posix())
        except ValueError:
            continue
    return sorted(set(values)), bool(paths)


def build(
    root_value: str | Path,
    includes: Iterable[str] = (),
    excludes: Iterable[str] = (),
    *,
    with_hash: bool = False,
    output: str | Path | None = None,
    output_format: str = "json",
) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    include_rules = list(includes)
    exclude_rules = list(excludes)
    invalid_rules: list[dict[str, str]] = []
    normalized_includes: list[str] = []
    normalized_excludes: list[str] = []
    for kind, values, target in (
        ("include", include_rules, normalized_includes),
        ("exclude", exclude_rules, normalized_excludes),
    ):
        for value in values:
            normalized, error = _validate_rule(str(value))
            if error:
                invalid_rules.append({"rule": str(value), "kind": kind, "reason": error})
            elif normalized is not None:
                target.append(normalized)

    duplicates: list[str] = []
    seen_rules: set[str] = set()
    for rule in normalized_includes:
        if rule in seen_rules:
            duplicates.append(rule)
        seen_rules.add(rule)

    missing: list[str] = []
    path_hits: dict[str, tuple[str, int]] = {}
    selected: set[str] = set()
    if root.is_dir():
        if normalized_includes:
            for rule in normalized_includes:
                expanded, had_any = _expand(root, rule)
                if not had_any or not expanded:
                    # A wildcard that simply matches no files is still a
                    # missing explicit rule; this makes manifests fail closed.
                    missing.append(rule)
                for relative in expanded:
                    key = os.path.normcase(relative).casefold()
                    first, count = path_hits.get(key, (relative, 0))
                    path_hits[key] = (first, count + 1)
                selected.update(expanded)
        else:
            selected.update(_all_files(root))
    else:
        missing.append("<project_root>")

    # Built-in exclusions are intentionally conservative and cannot be
    # overridden by an include rule.
    all_candidates = _all_files(root) if root.is_dir() else []
    blocked: list[str] = []
    duplicates.extend(relative for relative, count in path_hits.values() if count > 1)
    for relative in sorted(selected):
        if _is_local_only(relative):
            blocked.append(relative)
    for relative in blocked:
        selected.discard(relative)
    if blocked and normalized_includes:
        direct_local_rules = {
            rule
            for rule in normalized_includes
            if _is_local_only(rule) or any(part in LOCAL_ONLY_PARTS for part in PurePosixPath(rule).parts)
        }
        invalid_rules.extend(
            {"rule": rule, "kind": "include", "reason": "local_only_path"}
            for rule in sorted(direct_local_rules)
        )

    excluded: list[str] = []
    for relative in sorted(set(all_candidates) | set(selected)):
        if any(_matches(relative, pattern) for pattern in normalized_excludes):
            if relative in selected:
                selected.discard(relative)
                excluded.append(relative)

    if normalized_includes:
        unknown_extra = sorted(
            path
            for path in all_candidates
            if path not in selected
            and path not in blocked
            and not any(_matches(path, pattern) for pattern in normalized_excludes)
        )
    else:
        unknown_extra = []

    entries: list[dict[str, Any]] = []
    for relative in sorted(selected):
        path = root / Path(relative)
        try:
            data = path.read_bytes()
        except OSError as exc:
            invalid_rules.append({"rule": relative, "kind": "file", "reason": type(exc).__name__})
            continue
        entry: dict[str, Any] = {"path": relative, "size": len(data)}
        if with_hash:
            entry["sha256"] = hashlib.sha256(data).hexdigest()
        entries.append(entry)

    result: dict[str, Any] = {
        "project_root": str(root),
        "files": [entry["path"] for entry in entries],
        "entries": entries,
        "include_rules": normalized_includes,
        "exclude_rules": normalized_excludes,
        "schema_version": 1,
        "hash_algorithm": "sha256" if with_hash else "none",
        "paths": [entry["path"] for entry in entries],
        "count": len(entries),
        "missing": sorted(set(missing)),
        "missing_paths": sorted(set(missing)),
        "duplicates": sorted(set(duplicates)),
        "duplicate_paths": sorted(set(duplicates)),
        "unknown_extra": unknown_extra,
        "unknown_extra_files": unknown_extra,
        "excluded": sorted(set(excluded)),
        "excluded_paths": [
            {"path": path, "reason": "explicit_exclude"} for path in sorted(set(excluded))
        ]
        + [{"path": path, "reason": "local_only"} for path in sorted(set(blocked))],
        "local_only_excluded": sorted(set(blocked)),
        "invalid_rules": invalid_rules,
        "errors": invalid_rules,
        "valid": bool(
            root.is_dir()
            and not missing
            and not duplicates
            and not unknown_extra
            and not invalid_rules
        ),
        "github_write_performed": False,
        "git_staging_performed": False,
    }

    if output and result["valid"]:
        output_path = Path(output).expanduser()
        if not output_path.is_absolute():
            output_path = root / output_path
        if output_path.exists():
            raise FileExistsError("output_exists")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            if output_format == "json"
            else "".join(f"{path}\n" for path in result["files"])
        )
        with output_path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        result["output"] = str(output_path.resolve())
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--include", action="append", default=[])
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--include-file", "--manifest-file", "--manifest", dest="include_file")
    parser.add_argument("--exclude-file", dest="exclude_file")
    parser.add_argument("--hash", "--content-hash", dest="with_hash", action="store_true")
    parser.add_argument("--output")
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    includes = list(args.include)
    excludes = list(args.exclude)
    try:
        if args.include_file:
            file_includes, file_excludes = _read_rules(Path(args.include_file).expanduser().resolve())
            includes.extend(file_includes)
            excludes.extend(file_excludes)
        if args.exclude_file:
            file_rules, nested_excludes = _read_rules(Path(args.exclude_file).expanduser().resolve())
            excludes.extend(file_rules)
            excludes.extend(nested_excludes)
        result = build(
            args.project_root,
            includes,
            excludes,
            with_hash=args.with_hash,
            output=args.output,
            output_format="json" if args.json or args.format == "json" else "text",
        )
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        payload = {"valid": False, "error": type(exc).__name__, "github_write_performed": False}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if args.json else f"ERROR: {payload['error']}")
        return EXIT_USAGE

    emit_json = args.json or args.format == "json"
    if emit_json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        if result["valid"]:
            for path in result["files"]:
                print(path)
        else:
            print(f"missing={len(result['missing'])} unknown_extra={len(result['unknown_extra'])} invalid={len(result['invalid_rules'])}", file=sys.stderr)
    return EXIT_OK if result["valid"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
