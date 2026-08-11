"""Small stdlib smoke tests for the local, read-only Skill scripts."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load(name: str):
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScriptSmokeTests(unittest.TestCase):
    def test_all_python_scripts_compile(self) -> None:
        for path in sorted((ROOT / "scripts").glob("*.py")):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")

    def test_auth_never_reports_credential_values(self) -> None:
        module = load("inspect_auth")
        args = module._parser().parse_args(
            ["--expected-owner", "new-owner", "--remote", "https://github.com/owner/repo.git", "--json"]
        )
        result = module.inspect(args)
        self.assertTrue(result["credential_values_exposed"] is False)
        self.assertTrue(result["github_write_performed"] is False)
        self.assertTrue(result["stop_reason"])

    def test_manifest_excludes_local_report_and_rejects_duplicate_paths(self) -> None:
        module = load("build_release_manifest")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("ok\n", encoding="utf-8")
            (root / "PRE-PUBLISH-REPORT.md").write_text("local\n", encoding="utf-8")
            result = module.build(root, ["README.md", "PRE-PUBLISH-REPORT.md"])
            self.assertIn("PRE-PUBLISH-REPORT.md", result["local_only_excluded"])
            duplicate = module.build(root, ["README.md", "*.md"])
            self.assertTrue(duplicate["duplicates"] or not duplicate["valid"])

    def test_manifest_reports_only_root_workflow_files(self) -> None:
        module = load("build_release_manifest")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [
                "README.md",
                ".github/workflows/ci.yml",
                ".github/workflows/release/sub-workflow.yml",
                "docs/.github/workflows/example.md",
                "templates/.github/workflows/ci.yml",
            ]
            for relative in paths:
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok\n", encoding="utf-8")
            result = module.build(root, paths)
            self.assertTrue(result["workflow_files_present"])
            self.assertEqual(result["workflow_file_count"], 2)
            self.assertEqual(
                result["workflow_file_paths"],
                [
                    ".github/workflows/ci.yml",
                    ".github/workflows/release/sub-workflow.yml",
                ],
            )

    def test_auth_stops_before_repository_creation_without_workflow_scope(self) -> None:
        module = load("inspect_auth")
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(
                json.dumps({"files": ["README.md", ".github/workflows/ci.yml"]}),
                encoding="utf-8",
            )
            args = module._parser().parse_args(
                [
                    "--expected-owner", "new-owner",
                    "--cli-account", "new-owner",
                    "--api-account", "new-owner",
                    "--planned-push-protocol", "HTTPS",
                    "--push-credential-source", "GH_CLI_KEYRING",
                    "--scope-credential-source", "GH_CLI_KEYRING",
                    "--push-credential-type", "OAUTH",
                    "--oauth-scope", "repo",
                    "--manifest", str(manifest),
                    "--require-workflow-scope-when-applicable",
                ]
            )
            result = module.inspect(args)
            self.assertEqual(result["workflow_scope_status"], "MISSING")
            self.assertFalse(result["repository_creation_allowed"])
            self.assertFalse(result["push_allowed"])
            self.assertFalse(result["github_write_performed"])

    def test_auth_rejects_scope_evidence_without_matching_source(self) -> None:
        module = load("inspect_auth")
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_text(
                json.dumps({"files": [".github/workflows/ci.yml"]}),
                encoding="utf-8",
            )
            args = module._parser().parse_args(
                [
                    "--expected-owner", "new-owner",
                    "--cli-account", "new-owner",
                    "--api-account", "new-owner",
                    "--planned-push-protocol", "HTTPS",
                    "--push-credential-source", "GH_CLI_KEYRING",
                    "--push-credential-type", "OAUTH",
                    "--oauth-scope", "workflow",
                    "--manifest", str(manifest),
                ]
            )
            result = module.inspect(args)
            self.assertIsNone(result["credential_source_match"])
            self.assertEqual(result["workflow_scope_status"], "NOT_VERIFIED")
            self.assertFalse(result["repository_creation_allowed"])

    def test_utf8_and_markdown_fail_closed(self) -> None:
        utf8 = load("validate_utf8")
        links = load("check_markdown_links")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad = root / "bad.md"
            bad.write_bytes(b"\xff\xfe")
            result = utf8.validate([bad], root=root)
            self.assertFalse(result["valid"])
            doc = root / "README.md"
            doc.write_text("[missing](missing.md)\n", encoding="utf-8")
            link_result = links.check(root)
            self.assertFalse(link_result["valid"])

    def test_sensitive_scan_masks_finding(self) -> None:
        module = load("scan_sensitive_content")
        synthetic = "secret=" + "TOKENVALUE1234567890" + "\n"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / "settings.txt"
            file.write_text(synthetic, encoding="utf-8")
            result = module.scan(root)
            payload = json.dumps(result, ensure_ascii=False)
            self.assertFalse(result["valid"])
            self.assertNotIn("TOKENVALUE1234567890", payload)

    def test_artifact_scan_detects_secret(self) -> None:
        module = load("inspect_build_artifacts")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "dist.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("pkg/config.txt", "token=" + "TOKENVALUE1234567890" + "\n")
            result = module.inspect(root)
            self.assertTrue(result["artifact_count"] == 1)
            self.assertTrue(result["finding_count"] > 0)

    def test_skill_and_scenarios_validate(self) -> None:
        skill = load("validate_skill")
        scenario = load("run_scenario_tests")
        skill_result = skill.validate(ROOT)
        self.assertTrue(skill_result["valid"])
        self.assertTrue(skill_result["checks"]["workflow_scope_preflight"])
        result = scenario.run(ROOT / "tests")
        self.assertEqual(result["ALL_SCENARIOS_PASS"], "YES")
        self.assertEqual(result["NEW_SCENARIOS_RUN"], 10)
        self.assertEqual(result["NEW_SCENARIOS_PASS"], 10)
        self.assertEqual(result["GITHUB_WRITE_PERFORMED"], "NO")


if __name__ == "__main__":
    unittest.main()
