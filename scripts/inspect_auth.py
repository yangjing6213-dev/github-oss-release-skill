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
from pathlib import Path
from typing import Any


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2


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

    # This is an inspection, not an authorization grant.  A caller may opt in
    # to an explicit local authorization marker for a truthful readiness value.
    authorized = args.authorization == "APPROVE_GITHUB_PUBLISH"
    # Owner/remote metadata alone is not authentication evidence.  A verified
    # CLI/API/SSH identity must be present before reporting read readiness.
    read_ready = bool(known_accounts and account_match is True and not conflict)
    write_ready = bool(authorized and read_ready and not reasons)
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
            "read_ready",
            "write_ready",
            "stop_reason",
        ):
            print(f"{key} = {result[key]}")
    return EXIT_OK if not result["stop_reason"] else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
