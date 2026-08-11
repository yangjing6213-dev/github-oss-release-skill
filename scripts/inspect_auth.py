"""Read-only GitHub authentication/account inspection.

The command deliberately reports only presence and identities.  It never calls
the mutating/auth-token variants of ``gh auth`` and never prints credential
values (or derived metadata).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_WORKFLOW_SCOPE_MISSING = 2
EXIT_CREDENTIAL_SOURCE_MISMATCH = 3
EXIT_ACCOUNT_MISMATCH = 4
EXIT_PERMISSION_NOT_VERIFIED = 5
EXIT_USAGE = 64
PUSH_PROTOCOLS = {"HTTPS", "SSH", "OTHER", "NOT_CONFIGURED", "NOT_VERIFIED"}
PUSH_CREDENTIAL_SOURCES = {
    "GH_TOKEN_ENVIRONMENT",
    "GITHUB_TOKEN_ENVIRONMENT",
    "GH_CLI_KEYRING",
    "GIT_CREDENTIAL_MANAGER",
    "SSH_KEY",
    "OTHER",
    "NOT_VERIFIED",
}
PUSH_CREDENTIAL_TYPES = {
    "OAUTH",
    "CLASSIC_PAT",
    "FINE_GRAINED_PAT",
    "GITHUB_APP_TOKEN",
    "SSH",
    "OTHER",
    "NOT_VERIFIED",
}


def _account(value: str | None) -> str | None:
    """Extract an owner/login from a GitHub URL or plain value."""
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    # Avoid exposing URL credentials if a caller supplied a malformed remote.
    text = re.sub(r"^[a-z][a-z0-9+.-]*://[^/@\s]+@", "", text, flags=re.I)
    match = re.search(r"github\.com[/:]([^/\s:]+)/", text, flags=re.I)
    if match:
        value = match.group(1).strip()
        return value[:-4] if value.lower().endswith(".git") else value or None
    if "@" in text and ":" in text:
        text = text.rsplit(":", 1)[-1]
    text = text.strip("/ ").split("/", 1)[0]
    if text.lower().endswith(".git"):
        text = text[:-4]
    return text or None


def _remote_parts(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    text = re.sub(r"^[a-z][a-z0-9+.-]*://[^/@\s]+@", "", value.strip(), flags=re.I)
    match = re.search(r"github\.com[/:]([^/\s:]+)/([^\s/]+)", text, flags=re.I)
    if not match:
        return _account(text), None
    owner = match.group(1)
    repo = match.group(2).split("?", 1)[0].split("#", 1)[0]
    repo = repo[:-4] if repo.lower().endswith(".git") else repo
    return owner or None, repo or None


def _git_remote(remote_name: str = "origin") -> str | None:
    try:
        result = subprocess.run(
            ["git", "config", "--get", f"remote.{remote_name}.url"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip()
    return value or None


def _scope_presence(name: str) -> dict[str, bool | None]:
    """Return process/user/machine presence without revealing values."""
    process = bool(os.environ.get(name))
    user: bool | None = None
    machine: bool | None = None
    if os.name == "nt":
        try:
            import winreg  # type: ignore

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                try:
                    user = bool(winreg.QueryValueEx(key, name)[0])
                except OSError:
                    user = False
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
            ) as key:
                try:
                    machine = bool(winreg.QueryValueEx(key, name)[0])
                except OSError:
                    machine = False
        except (ImportError, OSError):
            # Presence in the inherited process is still useful when registry
            # access is unavailable.  Unknown scopes remain explicitly null.
            pass
    return {"process": process, "user": user, "machine": machine}


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value:
            return value.strip()
    return None


def _choice(value: str | None, allowed: set[str], default: str) -> str:
    normalized = str(value or "").strip().upper()
    return normalized if normalized in allowed else default


def _planned_protocol(remote: str | None, explicit: str | None) -> str:
    if explicit:
        return _choice(explicit, PUSH_PROTOCOLS, "NOT_VERIFIED")
    value = str(remote or "").strip().lower()
    if not value:
        return "NOT_CONFIGURED"
    if value.startswith(("https://", "http://")):
        return "HTTPS"
    if value.startswith("ssh://") or re.match(r"^[^@\s]+@[^:\s]+:", value):
        return "SSH"
    return "OTHER"


def _manifest_paths(path_value: str | None) -> list[str]:
    if not path_value:
        return []
    path = Path(path_value).expanduser().resolve()
    text = path.read_text(encoding="utf-8")
    try:
        value: Any = json.loads(text)
    except json.JSONDecodeError:
        value = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    if isinstance(value, dict):
        value = value.get("workflow_file_paths", value.get("files", value.get("paths", [])))
    if not isinstance(value, list):
        raise ValueError("manifest_paths_missing")
    paths: list[str] = []
    for item in value:
        candidate = item.get("path") if isinstance(item, dict) else item
        if isinstance(candidate, str):
            paths.append(candidate)
    return paths


def _workflow_paths(paths: list[str]) -> list[str]:
    result: set[str] = set()
    for value in paths:
        normalized = value.replace("\\", "/").strip()
        if normalized.startswith("./"):
            normalized = normalized[2:]
        path = PurePosixPath(normalized)
        windows = PureWindowsPath(normalized)
        if (
            normalized
            and not path.is_absolute()
            and not windows.is_absolute()
            and not windows.drive
            and ".." not in path.parts
            and len(path.parts) > 2
            and path.parts[:2] == (".github", "workflows")
        ):
            result.add(path.as_posix())
    return sorted(result)


def _safe_scope_names(values: list[str]) -> list[str]:
    scopes: set[str] = set()
    for value in values:
        for candidate in value.split(","):
            name = candidate.strip()
            if re.fullmatch(r"[A-Za-z0-9:_-]+", name):
                scopes.add(name)
    return sorted(scopes, key=str.casefold)


def inspect(args: argparse.Namespace) -> dict[str, Any]:
    remote_value = args.remote or _git_remote(args.remote_name)
    remote_owner, remote_repository = _remote_parts(remote_value)
    expected_owner = _account(args.expected_owner or _env_first("EXPECTED_OWNER"))

    cli_account = _account(args.cli_account or _env_first("CLI_ACCOUNT", "GH_CLI_ACCOUNT"))
    api_account = _account(args.api_account or _env_first("API_ACCOUNT", "GITHUB_API_ACCOUNT"))
    ssh_account = _account(args.ssh_account or _env_first("SSH_ACCOUNT", "GITHUB_SSH_ACCOUNT"))
    token_account = _account(
        args.token_account
        or _env_first("GITHUB_TOKEN_OWNER", "GH_TOKEN_OWNER", "ENVIRONMENT_TOKEN_OWNER")
    )

    gh_scopes = _scope_presence("GH_TOKEN")
    github_scopes = _scope_presence("GITHUB_TOKEN")
    gh_token_set = any(value is True for value in gh_scopes.values())
    github_token_set = any(value is True for value in github_scopes.values())
    planned_push_protocol = _planned_protocol(remote_value, args.planned_push_protocol)
    push_credential_source = _choice(
        args.push_credential_source,
        PUSH_CREDENTIAL_SOURCES,
        "GH_TOKEN_ENVIRONMENT"
        if gh_scopes["process"]
        else "GITHUB_TOKEN_ENVIRONMENT"
        if github_scopes["process"]
        else "SSH_KEY"
        if planned_push_protocol == "SSH"
        else "GH_CLI_KEYRING"
        if cli_account
        else "NOT_VERIFIED",
    )
    push_credential_type = _choice(
        args.push_credential_type,
        PUSH_CREDENTIAL_TYPES,
        "SSH" if push_credential_source == "SSH_KEY" else "NOT_VERIFIED",
    )
    scope_credential_source = _choice(
        args.scope_credential_source,
        PUSH_CREDENTIAL_SOURCES,
        "NOT_VERIFIED",
    )
    credential_source_match: bool | None = (
        None
        if scope_credential_source == "NOT_VERIFIED"
        else scope_credential_source == push_credential_source
    )
    oauth_scopes = _safe_scope_names(args.oauth_scope)
    oauth_scopes_inspectable = bool(args.oauth_scope)
    workflow_file_paths = _workflow_paths(_manifest_paths(args.manifest))
    workflow_files_present = bool(workflow_file_paths)
    workflow_scope_preflight_required = bool(
        workflow_files_present
        and planned_push_protocol == "HTTPS"
        and push_credential_type in {"OAUTH", "CLASSIC_PAT"}
    )

    if not workflow_files_present:
        workflow_scope_status = "NOT_APPLICABLE_NO_WORKFLOW_FILES"
    elif planned_push_protocol == "SSH":
        workflow_scope_status = "NOT_APPLICABLE_SSH_PUSH"
    elif planned_push_protocol != "HTTPS":
        workflow_scope_status = (
            "NOT_APPLICABLE_OR_REQUIRES_HOST_SPECIFIC_POLICY"
            if planned_push_protocol == "OTHER"
            else "NOT_VERIFIED"
        )
    elif push_credential_type in {"FINE_GRAINED_PAT", "GITHUB_APP_TOKEN"}:
        workflow_scope_status = "CREDENTIAL_TYPE_SPECIFIC_PERMISSION_REVIEW"
    elif push_credential_type not in {"OAUTH", "CLASSIC_PAT"}:
        workflow_scope_status = "NOT_VERIFIED"
    elif credential_source_match is not True:
        workflow_scope_status = "NOT_VERIFIED"
    elif oauth_scopes_inspectable:
        workflow_scope_status = (
            "PRESENT"
            if any(scope.casefold() == "workflow" for scope in oauth_scopes)
            else "MISSING"
        )
    else:
        workflow_scope_status = "NOT_VERIFIED"

    workflow_scope_preflight_result = (
        "PASS"
        if workflow_scope_status
        in {
            "PRESENT",
            "NOT_APPLICABLE_NO_WORKFLOW_FILES",
            "NOT_APPLICABLE_SSH_PUSH",
        }
        else "FAIL"
    )
    workflow_scope_refresh_required = workflow_scope_status == "MISSING"
    workflow_scope_refresh_authorized = (
        args.workflow_scope_refresh_authorization
        == "APPROVE_GITHUB_WORKFLOW_SCOPE_REFRESH"
    )

    known_accounts = [
        account
        for account in (cli_account, api_account, ssh_account)
        if account
    ]
    distinct_accounts = {account.lower() for account in known_accounts}
    conflict = bool(gh_token_set and github_token_set)
    if token_account and expected_owner and token_account.lower() != expected_owner.lower():
        conflict = True
    if token_account and known_accounts and any(
        token_account.lower() != account.lower() for account in known_accounts
    ):
        conflict = True

    target_accounts = list(known_accounts)
    if expected_owner:
        target_accounts.append(expected_owner)
    if remote_owner:
        target_accounts.append(remote_owner)
    distinct_target = {account.lower() for account in target_accounts}
    account_match: bool | None
    if not known_accounts:
        account_match = None
    else:
        account_match = len(distinct_target) == 1 and not conflict

    reasons: list[str] = []
    if conflict:
        reasons.append("ENVIRONMENT_TOKEN_CONFLICT")
    if expected_owner and known_accounts and any(
        account.lower() != expected_owner.lower() for account in known_accounts
    ):
        reasons.append("ACCOUNT_OWNER_MISMATCH")
    if expected_owner and remote_owner and remote_owner.lower() != expected_owner.lower():
        reasons.append("REMOTE_OWNER_MISMATCH")
    if not expected_owner and not known_accounts:
        reasons.append("EXPECTED_OWNER_OR_ACCOUNT_UNKNOWN")
    if credential_source_match is False:
        reasons.append("PUSH_CREDENTIAL_SOURCE_MISMATCH")
    if workflow_scope_preflight_required and workflow_scope_status != "PRESENT":
        reasons.append("WORKFLOW_SCOPE_PREFLIGHT_FAILED")
    elif workflow_files_present and workflow_scope_preflight_result != "PASS":
        reasons.append("WORKFLOW_PERMISSION_NOT_VERIFIED")

    # This is an inspection, not an authorization grant.  A caller may opt in
    # to an explicit local authorization marker for a truthful readiness value.
    authorized = args.authorization == "APPROVE_GITHUB_PUBLISH"
    # Owner/remote metadata alone is not authentication evidence.  A verified
    # CLI/API/SSH identity must be present before reporting read readiness.
    read_ready = bool(known_accounts and account_match is True and not conflict)
    repository_creation_allowed = bool(
        read_ready and workflow_scope_preflight_result == "PASS"
    )
    push_allowed = repository_creation_allowed
    write_ready = bool(authorized and push_allowed and not reasons)
    if not write_ready and authorized and not reasons:
        reasons.append("AUTHENTICATION_NOT_VERIFIED")
    stop_reason = "; ".join(dict.fromkeys(reasons)) or None

    return {
        "expected_owner": expected_owner,
        "gh_token_set": gh_token_set,
        "github_token_set": github_token_set,
        "token_scopes": {"GH_TOKEN": gh_scopes, "GITHUB_TOKEN": github_scopes},
        "cli_account": cli_account,
        "api_account": api_account,
        "ssh_account": ssh_account,
        "remote_owner": remote_owner,
        "remote_repository": remote_repository,
        "account_match": account_match,
        "environment_token_conflict": conflict,
        "planned_push_protocol": planned_push_protocol,
        "push_credential_source": push_credential_source,
        "push_credential_type": push_credential_type,
        "scope_credential_source": scope_credential_source,
        "credential_source_match": credential_source_match,
        "oauth_scopes": oauth_scopes,
        "oauth_scopes_inspectable": oauth_scopes_inspectable,
        "workflow_files_present": workflow_files_present,
        "workflow_file_count": len(workflow_file_paths),
        "workflow_file_paths": workflow_file_paths,
        "workflow_scope_status": workflow_scope_status,
        "workflow_scope_preflight_required": workflow_scope_preflight_required,
        "workflow_scope_preflight_result": workflow_scope_preflight_result,
        "workflow_scope_refresh_required": workflow_scope_refresh_required,
        "workflow_scope_refresh_authorized": workflow_scope_refresh_authorized,
        "repository_creation_allowed": repository_creation_allowed,
        "push_allowed": push_allowed,
        "read_ready": read_ready,
        "write_ready": write_ready,
        "stop_reason": stop_reason,
        "credential_values_exposed": False,
        "github_write_performed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-owner", "--owner", dest="expected_owner")
    parser.add_argument("--remote", "--remote-url", dest="remote")
    parser.add_argument("--remote-name", default="origin")
    parser.add_argument("--cli-account")
    parser.add_argument("--api-account")
    parser.add_argument("--ssh-account")
    parser.add_argument("--token-account")
    parser.add_argument("--planned-push-protocol", choices=sorted(PUSH_PROTOCOLS))
    parser.add_argument("--push-credential-source", choices=sorted(PUSH_CREDENTIAL_SOURCES))
    parser.add_argument("--scope-credential-source", choices=sorted(PUSH_CREDENTIAL_SOURCES))
    parser.add_argument("--push-credential-type", choices=sorted(PUSH_CREDENTIAL_TYPES))
    parser.add_argument("--oauth-scope", action="append", default=[])
    parser.add_argument("--manifest")
    parser.add_argument(
        "--require-workflow-scope-when-applicable",
        action="store_true",
    )
    parser.add_argument(
        "--workflow-scope-refresh-authorization",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--authorization", help=argparse.SUPPRESS)
    parser.add_argument("--json", action="store_true", help="emit JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        result = inspect(args)
    except Exception as exc:  # pragma: no cover - defensive boundary
        payload = {
            "valid": False,
            "error": type(exc).__name__,
            "credential_values_exposed": False,
            "github_write_performed": False,
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"ERROR: {payload['error']}")
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for key in (
            "expected_owner",
            "gh_token_set",
            "github_token_set",
            "cli_account",
            "api_account",
            "ssh_account",
            "remote_owner",
            "account_match",
            "environment_token_conflict",
            "planned_push_protocol",
            "push_credential_source",
            "push_credential_type",
            "credential_source_match",
            "workflow_files_present",
            "workflow_scope_status",
            "workflow_scope_preflight_required",
            "workflow_scope_preflight_result",
            "workflow_scope_refresh_required",
            "repository_creation_allowed",
            "push_allowed",
            "read_ready",
            "write_ready",
            "stop_reason",
        ):
            print(f"{key} = {result[key]}")
    if result["credential_source_match"] is False:
        return EXIT_CREDENTIAL_SOURCE_MISMATCH
    if result["account_match"] is False:
        return EXIT_ACCOUNT_MISMATCH
    if result["workflow_scope_status"] == "MISSING":
        return EXIT_WORKFLOW_SCOPE_MISSING
    if (
        result["workflow_files_present"]
        and result["workflow_scope_preflight_result"] != "PASS"
    ):
        return EXIT_PERMISSION_NOT_VERIFIED
    return EXIT_OK if not result["stop_reason"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
