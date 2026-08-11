"""Run deterministic local control-harness scenarios for the release Skill.

This runner does not claim to reproduce a fresh-agent evaluation.  It checks
the machine-readable safety contract against fixtures and labels that limit
explicitly in every result.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable


EXIT_OK = 0
EXIT_FINDINGS = 1
EXIT_USAGE = 2
REQUIRED_RECORD_FIELDS = {
    "SCENARIO",
    "INPUT_PRESSURES",
    "ACTUAL_BEHAVIOR",
    "EXPECTED_SAFE_BEHAVIOR",
    "FAILURE_FOUND",
    "RATIONALE_USED",
    "RISK",
}
RED_IDS = {f"RED-{number:02d}" for number in range(1, 11)}
GREEN_IDS = {f"GREEN-{number:02d}" for number in range(11, 21)}
RESUME_IDS = {"RESUME-01"}
WORKFLOW_IDS = {f"WS-{number:02d}" for number in range(1, 11)}


def _normalize_id(value: Any) -> str:
    return str(value or "").strip().upper()


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _records(value: Any, *, source: Path, expected: bool = False) -> list[dict[str, Any]]:
    if isinstance(value, list):
        values = value
    elif isinstance(value, dict):
        if expected and isinstance(value.get("expected"), (dict, list)):
            values = value["expected"]
            if isinstance(values, dict):
                return [{"SCENARIO": key, **(item if isinstance(item, dict) else {"expected": item})} for key, item in values.items()]
        elif isinstance(value.get("scenarios"), list):
            values = value["scenarios"]
        elif "SCENARIO" in value or "id" in value:
            values = [value]
        else:
            # An expected map is accepted even without an `expected` wrapper.
            if expected:
                return [{"SCENARIO": key, **(item if isinstance(item, dict) else {"expected": item})} for key, item in value.items()]
            raise ValueError(f"{source.name}:scenario_list_missing")
    else:
        raise ValueError(f"{source.name}:scenario_data_must_be_object_or_list")
    records: list[dict[str, Any]] = []
    for item in values:
        if not isinstance(item, dict):
            raise ValueError(f"{source.name}:scenario_record_not_object")
        records.append(dict(item))
    return records


def _safe_relative(path: Path, root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return not any(part == ".." for part in relative.parts)


def discover(tests_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], list[str]]:
    scenarios_dir = tests_root / "scenarios"
    expected_dir = tests_root / "expected-results"
    errors: list[str] = []
    scenarios: dict[str, dict[str, Any]] = {}
    expected: dict[str, dict[str, Any]] = {}
    if not scenarios_dir.is_dir() or not expected_dir.is_dir():
        return scenarios, expected, ["scenario_directories_missing"]

    for path in sorted(scenarios_dir.glob("*.json"), key=lambda item: item.name.casefold()):
        if not _safe_relative(path, tests_root):
            errors.append(f"unsafe_scenario_path:{path.name}")
            continue
        try:
            records = _records(_load(path), source=path)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"scenario_load:{path.name}:{type(exc).__name__}")
            continue
        for record in records:
            scenario_id = _normalize_id(record.get("SCENARIO", record.get("id")))
            if not scenario_id:
                errors.append(f"scenario_id_missing:{path.name}")
                continue
            if scenario_id in scenarios:
                errors.append(f"duplicate_scenario:{scenario_id}")
                continue
            record["SCENARIO"] = scenario_id
            scenarios[scenario_id] = record

    fixtures_dir = tests_root / "fixtures"
    if fixtures_dir.is_dir():
        for path in sorted(fixtures_dir.glob("*.json"), key=lambda item: item.name.casefold()):
            try:
                fixture_records = _records(_load(path), source=path)
            except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"fixture_load:{path.name}:{type(exc).__name__}")
                continue
            for fixture in fixture_records:
                scenario_id = _normalize_id(fixture.get("SCENARIO", fixture.get("id")))
                if not scenario_id:
                    errors.append(f"fixture_id_missing:{path.name}")
                elif scenario_id not in scenarios:
                    errors.append(f"orphan_fixture:{scenario_id}")
                else:
                    merged = dict(scenarios[scenario_id])
                    merged.update(fixture)
                    scenarios[scenario_id] = merged

    for path in sorted(expected_dir.glob("*.json"), key=lambda item: item.name.casefold()):
        try:
            records = _records(_load(path), source=path, expected=True)
        except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"expected_load:{path.name}:{type(exc).__name__}")
            continue
        for record in records:
            scenario_id = _normalize_id(record.get("SCENARIO", record.get("id")))
            if not scenario_id:
                errors.append(f"expected_id_missing:{path.name}")
                continue
            if scenario_id in expected:
                errors.append(f"duplicate_expected:{scenario_id}")
                continue
            record["SCENARIO"] = scenario_id
            expected[scenario_id] = record

    scenario_stems = {path.stem.upper() for path in scenarios_dir.glob("*.json")}
    expected_stems = {path.stem.upper() for path in expected_dir.glob("*.json")}
    # Aggregate files (scenarios.json/expected-results.json) carry their own
    # IDs and are not required to have matching filenames.
    if len(scenario_stems) == len(scenarios) and scenario_stems != expected_stems and not ("ALL" in scenario_stems and "ALL" in expected_stems):
        # Only report clear per-file orphans; aggregate maps are valid.
        for stem in sorted(expected_stems - scenario_stems):
            if stem not in {"ALL", "SCENARIOS"}:
                errors.append(f"orphan_expected_file:{stem}")
    return scenarios, expected, errors


def _pressures(record: dict[str, Any]) -> dict[str, Any]:
    value = record.get("INPUT_PRESSURES", record.get("input", {}))
    return value if isinstance(value, dict) else {}


def _truthy(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().upper() in {"YES", "TRUE", "1", "PASS"}
    return bool(value)


def _workflow_paths(values: Any) -> list[str]:
    result: set[str] = set()
    for value in values if isinstance(values, list) else []:
        normalized = str(value).replace("\\", "/").strip()
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


def _workflow_scope_policy(record: dict[str, Any]) -> dict[str, Any]:
    pressure = {str(key).upper(): value for key, value in _pressures(record).items()}
    paths = _workflow_paths(pressure.get("PUBLIC_MANIFEST", []))
    protocol = str(pressure.get("PLANNED_PUSH_PROTOCOL", "NOT_VERIFIED")).upper()
    credential_source = str(
        pressure.get("PUSH_CREDENTIAL_SOURCE", "NOT_VERIFIED")
    ).upper()
    scope_source = str(
        pressure.get("SCOPE_CREDENTIAL_SOURCE", credential_source)
    ).upper()
    credential_type = str(
        pressure.get("PUSH_CREDENTIAL_TYPE", "NOT_VERIFIED")
    ).upper()
    source_match = credential_source == scope_source
    required = bool(
        paths
        and protocol == "HTTPS"
        and credential_type in {"OAUTH", "CLASSIC_PAT"}
    )
    evidence_invalidated = _truthy(
        pressure.get("MANIFEST_CHANGED_AFTER_PREFLIGHT")
    )

    if not paths:
        scope_status = "NOT_APPLICABLE_NO_WORKFLOW_FILES"
    elif protocol == "SSH":
        scope_status = "NOT_APPLICABLE_SSH_PUSH"
    elif protocol != "HTTPS":
        scope_status = (
            "NOT_APPLICABLE_OR_REQUIRES_HOST_SPECIFIC_POLICY"
            if protocol == "OTHER"
            else "NOT_VERIFIED"
        )
    elif credential_type in {"FINE_GRAINED_PAT", "GITHUB_APP_TOKEN"}:
        scope_status = "CREDENTIAL_TYPE_SPECIFIC_PERMISSION_REVIEW"
    elif credential_type not in {"OAUTH", "CLASSIC_PAT"} or not source_match:
        scope_status = "NOT_VERIFIED"
    else:
        scope_status = str(
            pressure.get("WORKFLOW_SCOPE_STATUS", "NOT_VERIFIED")
        ).upper()

    refresh_authorized = (
        pressure.get("APPROVE_GITHUB_WORKFLOW_SCOPE_REFRESH")
        == "RECEIVED"
    )
    if (
        scope_status == "MISSING"
        and refresh_authorized
        and str(pressure.get("REFRESH_SIMULATED_RESULT", "")).upper()
        == "PRESENT"
        and _truthy(pressure.get("ACCOUNT_MATCH"))
        and source_match
    ):
        scope_status = "PRESENT"
    if evidence_invalidated:
        scope_status = "NOT_VERIFIED"

    preflight_pass = scope_status in {
        "PRESENT",
        "NOT_APPLICABLE_NO_WORKFLOW_FILES",
        "NOT_APPLICABLE_SSH_PUSH",
    }
    task_type = str(pressure.get("TASK_TYPE", "")).upper()
    repository_creation_allowed = bool(
        task_type == "INITIAL_PUBLICATION" and preflight_pass
    )
    push_allowed = preflight_pass
    remote_exists = _truthy(
        pressure.get("REMOTE_REPOSITORY_ALREADY_EXISTS")
    )
    return {
        "workflow_files_present": bool(paths),
        "workflow_file_count": len(paths),
        "workflow_file_paths": paths,
        "planned_push_protocol": protocol,
        "push_credential_source": credential_source,
        "push_credential_type": credential_type,
        "push_credential_source_match": source_match,
        "workflow_scope_preflight_required": required,
        "workflow_scope_status": scope_status,
        "workflow_scope_preflight_result": "PASS" if preflight_pass else "FAIL",
        "workflow_scope_refresh_required": scope_status == "MISSING",
        "workflow_scope_refresh_authorized": refresh_authorized,
        "workflow_scope_evidence_invalidated": evidence_invalidated,
        "repository_creation_allowed": repository_creation_allowed,
        "push_allowed": push_allowed,
        "repository_created": False,
        "remote_repository_already_exists": remote_exists,
        "workflow_scope_check_before_push": "PASS" if push_allowed else "FAIL",
        "github_write_performed": False,
    }


def _policy(record: dict[str, Any]) -> dict[str, Any]:
    pressure = {str(key).upper(): value for key, value in _pressures(record).items()}
    risk_keys = {
        "WORKTREE_DIRTY",
        "HISTORY_CONTAINS_UNVERIFIED_COVER",
        "PUSH_PROTECTION_BLOCKED",
        "CURRENT_TASK_BLOCKED",
        "TARGET_REPOSITORY_NONEMPTY",
        "ENVIRONMENT_TOKEN_CONFLICT",
        "PUBLIC_MANIFEST_INCLUDES_REPORT",
    }
    platform_status = str(pressure.get("HTTP_STATUS", ""))
    risk = any(_truthy(pressure.get(key)) for key in risk_keys) or platform_status in {"401", "403", "429"}
    force_requested = "FORCE" in str(pressure.get("USER_REQUEST", "")).upper()
    stop = risk or (force_requested and _truthy(pressure.get("TARGET_REPOSITORY_NONEMPTY")))
    if pressure.get("EXPECTED_OWNER") and pressure.get("REMOTE_OWNER") and str(pressure["EXPECTED_OWNER"]).lower() != str(pressure["REMOTE_OWNER"]).lower():
        stop = True
    if str(pressure.get("TESTS_CONFIGURED", "")).upper() == "NO":
        status = "not_configured"
    else:
        status = None
    published = str(pressure.get("REPOSITORY_PUBLISHED", "")).upper() == "YES"
    ci_status = str(pressure.get("CI_STATUS", "")).upper()
    if status == "not_configured":
        pass
    elif published and _truthy(pressure.get("CURRENT_TASK_BLOCKED")):
        status = "published_task_blocked"
    elif published and ci_status == "PENDING":
        status = "published_ci_pending"
    elif published and ci_status in {"FAIL", "FAILED"}:
        status = "published_ci_failed"
    elif published:
        status = "published"
    elif stop:
        status = "safely_paused"
    else:
        status = "ready_or_read_only"
    return {
        "no_write": True,
        "stop_on_risk": stop,
        "preserve_published_fact": published,
        "status": status,
        "force_push": False,
        "secret_output": False,
    }


def _resume_policy(record: dict[str, Any]) -> dict[str, Any]:
    pressure = _pressures(record)
    changed = {str(item).upper() for item in pressure.get("CHANGED_FILES", [])}
    only_support = changed == {"SUPPORT.MD"} or changed == {"SUPPORT.MD", "SUPPORT.MD"}
    return {
        "resume_from_checkpoint": _truthy(pressure.get("RESUME_FROM_CHECKPOINT", only_support)),
        "invalidated_gates": sorted(pressure.get("INVALIDATED_GATES", ["MARKDOWN_LINK_GATE", "README_LINK_GATE", "FINAL_INTEGRITY_GATE"])),
        "reused_gates": sorted(pressure.get("REUSED_GATES", ["HISTORY_SCAN", "LICENSE_AUDIT", "DEPENDENCY_AUDIT"])),
        "final_integrity_rerun": _truthy(pressure.get("FINAL_INTEGRITY_RERUN", True)),
        "report_excluded": _truthy(pressure.get("REPORT_EXCLUDED", True)),
        "support_only_change": only_support,
    }


def _compare(actual: dict[str, Any], expected: dict[str, Any], *, resume: bool = False) -> list[str]:
    failures: list[str] = []
    keys = (
        ("RESUME_FROM_CHECKPOINT", "resume_from_checkpoint"),
        ("INVALIDATED_GATES", "invalidated_gates"),
        ("REUSED_GATES", "reused_gates"),
        ("FINAL_INTEGRITY_RERUN", "final_integrity_rerun"),
        ("REPORT_EXCLUDED", "report_excluded"),
    ) if resume else (
        ("no_write", "no_write"),
        ("stop_on_risk", "stop_on_risk"),
        ("preserve_published_fact", "preserve_published_fact"),
        ("expected_status", "status"),
        ("force_push", "force_push"),
        ("secret_output", "secret_output"),
    )
    for expected_key, actual_key in keys:
        if expected_key not in expected:
            continue
        wanted = expected[expected_key]
        got = actual.get(actual_key)
        if isinstance(wanted, list):
            if sorted(wanted) != sorted(got or []):
                failures.append(expected_key)
        elif wanted != got:
            failures.append(expected_key)
    return failures


def _compare_workflow(actual: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key, wanted in expected.items():
        if str(key).upper() == "SCENARIO":
            continue
        actual_key = str(key).lower()
        got = actual.get(actual_key)
        if isinstance(wanted, list):
            if sorted(wanted) != sorted(got or []):
                failures.append(str(key))
        elif wanted != got:
            failures.append(str(key))
    return failures


def run(tests_root_value: str | Path, *, phase: str = "all", selected: Iterable[str] = ()) -> dict[str, Any]:
    tests_root = Path(tests_root_value).expanduser().resolve()
    scenarios, expected_map, discovery_errors = discover(tests_root)
    selected_ids = {_normalize_id(value) for value in selected if _normalize_id(value)}
    if selected_ids:
        ids = selected_ids
    elif phase == "red":
        ids = RED_IDS
    elif phase == "green":
        ids = GREEN_IDS
    elif phase == "resume":
        ids = RESUME_IDS
    elif phase == "workflow":
        ids = WORKFLOW_IDS
    else:
        ids = RED_IDS | GREEN_IDS | RESUME_IDS | WORKFLOW_IDS
    results: list[dict[str, Any]] = []
    errors = list(discovery_errors)
    for scenario_id in sorted(ids):
        record = scenarios.get(scenario_id)
        expected = expected_map.get(scenario_id, {})
        if record is None:
            errors.append(f"scenario_missing:{scenario_id}")
            continue
        missing_fields = sorted(REQUIRED_RECORD_FIELDS - set(record))
        if missing_fields:
            errors.append(f"record_fields_missing:{scenario_id}:{','.join(missing_fields)}")
            continue
        effective_expected = expected.get("EXPECTED_SAFE_BEHAVIOR", expected)
        if not isinstance(effective_expected, dict):
            effective_expected = {}
        if not expected or not effective_expected:
            errors.append(f"expected_missing:{scenario_id}")
        is_workflow = scenario_id in WORKFLOW_IDS
        actual = (
            _workflow_scope_policy(record)
            if is_workflow
            else _resume_policy(record)
            if scenario_id in RESUME_IDS
            else _policy(record)
        )
        failures = (
            _compare_workflow(actual, effective_expected)
            if is_workflow
            else _compare(
                actual,
                effective_expected,
                resume=scenario_id in RESUME_IDS,
            )
        )
        # Expected assertions may live inline under EXPECTED_SAFE_BEHAVIOR.
        inline = record.get("EXPECTED_SAFE_BEHAVIOR")
        if isinstance(inline, dict):
            failures.extend(
                _compare_workflow(actual, inline)
                if is_workflow
                else _compare(
                    actual,
                    inline,
                    resume=scenario_id in RESUME_IDS,
                )
            )
        if scenario_id.startswith("GREEN-") and str(record.get("GREEN_RESULT", effective_expected.get("GREEN_RESULT", "PASS"))).upper() != "PASS":
            failures.append("GREEN_RESULT")
        results.append({
            "SCENARIO": scenario_id,
            "INPUT_PRESSURES": record.get("INPUT_PRESSURES", {}),
            "ACTUAL_BEHAVIOR": record.get("ACTUAL_BEHAVIOR", ""),
            "EXPECTED_SAFE_BEHAVIOR": record.get("EXPECTED_SAFE_BEHAVIOR", {}),
            "FAILURE_FOUND": record.get("FAILURE_FOUND", False),
            "RATIONALE_USED": record.get("RATIONALE_USED", ""),
            "RISK": record.get("RISK", ""),
            "GREEN_RESULT": "PASS" if not failures else "FAIL",
            "actual": actual,
            "failures": sorted(set(failures)),
        })

    red_items = [item for item in results if item["SCENARIO"] in RED_IDS]
    red_run = len(red_items)
    green_results = [item for item in results if item["SCENARIO"] in GREEN_IDS]
    workflow_results = [
        item for item in results if item["SCENARIO"] in WORKFLOW_IDS
    ]
    resume_result = next((item for item in results if item["SCENARIO"] in RESUME_IDS), None)
    full_selection = not selected_ids and phase == "all"
    existing_results = [
        item
        for item in results
        if item["SCENARIO"] in RED_IDS | GREEN_IDS | RESUME_IDS
    ]
    existing_pass = bool(existing_results) and all(
        item["GREEN_RESULT"] == "PASS" for item in existing_results
    )
    workflow_pass = (
        len(workflow_results) == len(WORKFLOW_IDS)
        and all(item["GREEN_RESULT"] == "PASS" for item in workflow_results)
    )
    all_pass = (
        full_selection
        and not errors
        and RED_IDS.issubset(scenarios)
        and GREEN_IDS.issubset(scenarios)
        and RESUME_IDS.issubset(scenarios)
        and WORKFLOW_IDS.issubset(scenarios)
        and existing_pass
        and workflow_pass
    )
    if not scenarios:
        errors.append("NOT_CONFIGURED")
        all_pass = False
    return {
        "test_mode": "ISOLATED_CONTROL_HARNESS",
        "AGENT_BEHAVIOR_BASELINE": "NOT_FULLY_AVAILABLE",
        "RED_SCENARIOS_RUN": red_run,
        "RED_FAILURES_OBSERVED": sum(_truthy(scenarios[item["SCENARIO"]].get("FAILURE_FOUND")) for item in red_items),
        "RED_BASELINE_REPLAYED": red_run,
        "GREEN_SCENARIOS_RUN": red_run + len(green_results) if full_selection else len(green_results),
        "GREEN_SCENARIOS_PASS": sum(item["GREEN_RESULT"] == "PASS" for item in red_items + green_results),
        "ADDITIONAL_GREEN": len(green_results),
        "NEW_SCENARIOS_RUN": len(workflow_results),
        "NEW_SCENARIOS_PASS": sum(
            item["GREEN_RESULT"] == "PASS" for item in workflow_results
        ),
        "GREEN_WORKFLOW_SCOPE_SCENARIOS": (
            f"{sum(item['GREEN_RESULT'] == 'PASS' for item in workflow_results)} / "
            f"{len(workflow_results)} PASS"
        ),
        "ALL_EXISTING_SCENARIOS_PASS": "YES" if existing_pass else "NO",
        "ALL_NEW_SCENARIOS_PASS": "YES" if workflow_pass else "NO",
        "RESUME_FROM_CHECKPOINT": "PASS" if resume_result and resume_result["GREEN_RESULT"] == "PASS" else "NOT_CONFIGURED" if not resume_result else "FAIL",
        "ALL_SCENARIOS_PASS": "YES" if all_pass else "NO",
        "results": results,
        "errors": sorted(set(errors)),
        "GITHUB_WRITE_PERFORMED": "NO",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests-root", default=Path(__file__).resolve().parents[1] / "tests")
    parser.add_argument(
        "--phase",
        choices=("all", "red", "green", "resume", "workflow"),
        default="all",
    )
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        result = run(args.tests_root, phase=args.phase, selected=args.scenario)
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        payload = {"ALL_SCENARIOS_PASS": "NO", "errors": [type(exc).__name__], "GITHUB_WRITE_PERFORMED": "NO"}
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) if args.json else f"ERROR: {payload['errors'][0]}")
        return EXIT_USAGE
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        for item in result["results"]:
            print(f"{item['SCENARIO']}: {item['GREEN_RESULT']}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
        print(f"ALL_SCENARIOS_PASS = {result['ALL_SCENARIOS_PASS']}")
    return EXIT_OK if result["ALL_SCENARIOS_PASS"] == "YES" else EXIT_FINDINGS


if __name__ == "__main__":
    sys.exit(main())
