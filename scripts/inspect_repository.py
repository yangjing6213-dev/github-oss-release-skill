"""Read-only discovery of a local project's Git and release metadata."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2

STANDARD_FILES = (
    "README.md",
    "README.en.md",
    "README.zh-CN.md",
    "LICENSE",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CODE_OF_CONDUCT.md",
    "AGENTS.md",
    "docs/REPOSITORY_STANDARD.md",
    ".gitignore",
    ".env.example",
    ".github",
)
METADATA_NAMES = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "VERSION",
    "version.txt",
)


def _run_git(root: Path, *args: str) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, "", type(exc).__name__
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _remote_parts(url: str) -> tuple[str | None, str | None]:
    # Remove URL credentials before reporting anything.
    safe = re.sub(r"^[a-z][a-z0-9+.-]*://[^/@\s]+@", "", url.strip(), flags=re.I)
    match = re.search(r"github\.com[/:]([^/\s:]+)/([^\s/]+)", safe, flags=re.I)
    if not match:
        return None, None
    owner = match.group(1)
    repository = match.group(2).split("?", 1)[0].split("#", 1)[0]
    if repository.lower().endswith(".git"):
        repository = repository[:-4]
    return owner or None, repository or None


def _version(root: Path) -> str | None:
    candidates = [root / "VERSION", root / "version.txt"]
    for candidate in candidates:
        if candidate.is_file():
            try:
                value = candidate.read_text(encoding="utf-8").strip().splitlines()[0]
            except (OSError, UnicodeError, IndexError):
                continue
            if value:
                return value[:120]
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            import tomllib

            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            for table in (
                data.get("project", {}),
                data.get("tool", {}).get("poetry", {}),
                data.get("tool", {}).get("setuptools", {}),
            ):
                if isinstance(table, dict) and table.get("version"):
                    return str(table["version"])
        except (OSError, UnicodeError, ValueError, ImportError):
            pass
    package = root / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            if data.get("version"):
                return str(data["version"])
        except (OSError, UnicodeError, ValueError, TypeError):
            pass
    cargo = root / "Cargo.toml"
    if cargo.is_file():
        try:
            import tomllib

            data = tomllib.loads(cargo.read_text(encoding="utf-8"))
            version = data.get("package", {}).get("version")
            if version:
                return str(version)
        except (OSError, UnicodeError, ValueError, ImportError):
            pass
    return None


def _project_name(root: Path) -> str:
    package = root / "package.json"
    if package.is_file():
        try:
            value = json.loads(package.read_text(encoding="utf-8")).get("name")
            if value:
                return str(value)
        except (OSError, UnicodeError, ValueError, TypeError):
            pass
    for filename in ("pyproject.toml", "Cargo.toml"):
        path = root / filename
        if not path.is_file():
            continue
        try:
            import tomllib

            data = tomllib.loads(path.read_text(encoding="utf-8"))
            tables = [data.get("project", {}), data.get("package", {})]
            for table in tables:
                if isinstance(table, dict) and table.get("name"):
                    return str(table["name"])
        except (OSError, UnicodeError, ValueError, ImportError):
            pass
    for filename in ("README.md", "README.en.md", "README.zh-CN.md"):
        path = root / filename
        if not path.is_file():
            continue
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                match = re.match(r"^\s*#\s+(.+?)\s*$", line)
                if match and match.group(1).strip():
                    return match.group(1).strip()[:120]
        except (OSError, UnicodeError):
            pass
    return root.name


def _project_type(root: Path, metadata: list[str]) -> str:
    kinds: list[str] = []
    if any(name in metadata for name in ("pyproject.toml", "setup.py", "setup.cfg")):
        kinds.append("python")
    if "package.json" in metadata:
        kinds.append("node")
    if "Cargo.toml" in metadata:
        kinds.append("rust")
    if "go.mod" in metadata:
        kinds.append("go")
    if not kinds:
        suffixes = {path.suffix.lower() for path in root.rglob("*") if path.is_file()}
        if ".rs" in suffixes:
            kinds.append("rust")
        elif ".py" in suffixes:
            kinds.append("python")
        elif ".js" in suffixes or ".ts" in suffixes:
            kinds.append("node")
    return "+".join(kinds) if kinds else "unknown"


def _dirty_categories(status: str) -> list[str]:
    categories: set[str] = set()
    for line in status.splitlines():
        if not line:
            continue
        code = line[:2]
        if code == "??":
            categories.add("untracked")
        elif "R" in code:
            categories.add("renamed")
        elif "D" in code:
            categories.add("deleted")
        elif "M" in code or "A" in code or "C" in code:
            categories.add("modified")
        else:
            categories.add("other")
    return sorted(categories)


def inspect(root_value: str | Path) -> dict[str, Any]:
    root = Path(root_value).expanduser().resolve()
    is_git = False
    branch: str | None = None
    head: str | None = None
    remotes: dict[str, str] = {}
    status = ""
    if root.exists():
        code, value, _ = _run_git(root, "rev-parse", "--is-inside-work-tree")
        is_git = code == 0 and value.lower() == "true"
    if is_git:
        _, branch_value, _ = _run_git(root, "branch", "--show-current")
        branch = branch_value or None
        head_code, head_value, _ = _run_git(root, "rev-parse", "HEAD")
        head = head_value if head_code == 0 and head_value else None
        _, remote_text, _ = _run_git(root, "remote")
        for name in sorted(filter(None, remote_text.splitlines())):
            _, url, _ = _run_git(root, "config", "--get", f"remote.{name}.url")
            if url:
                # Keep only a credential-free URL.  This is still an observation,
                # never a request to alter origin.
                remotes[name] = re.sub(
                    r"^[a-z][a-z0-9+.-]*://[^/@\s]+@", "", url, flags=re.I
                )
        _, status, _ = _run_git(root, "status", "--porcelain=v1")

    metadata_files = sorted(
        name for name in METADATA_NAMES if (root / name).is_file()
    ) if root.exists() else []
    existing_standard = sorted(
        name for name in STANDARD_FILES if (root / name).exists()
    ) if root.exists() else []
    remote_url = remotes.get("origin")
    remote_owner, remote_repository = _remote_parts(remote_url or "")

    payload: dict[str, Any] = {
        "project_root": str(root),
        "is_git_repository": is_git,
        "worktree_clean": bool(is_git and not status),
        "branch": branch,
        "head": head,
        "remotes": remotes,
        "remote_owner": remote_owner,
        "remote_repository": remote_repository,
        "project_name": _project_name(root) if root.exists() else root.name,
        "project_version": _version(root) if root.exists() else None,
        "project_type": _project_type(root, metadata_files) if root.exists() else "unknown",
        "metadata_files": metadata_files,
        "existing_standard_files": existing_standard,
        "potential_dirty_categories": _dirty_categories(status),
        "github_write_performed": False,
    }
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = inspect(args.project_root)
    except Exception as exc:  # pragma: no cover - defensive boundary
        error = {"valid": False, "error": type(exc).__name__, "github_write_performed": False}
        print(json.dumps(error, ensure_ascii=False, sort_keys=True) if args.json else f"ERROR: {error['error']}")
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key, value in result.items():
            print(f"{key} = {value}")
    return EXIT_OK if result["is_git_repository"] and result["worktree_clean"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
