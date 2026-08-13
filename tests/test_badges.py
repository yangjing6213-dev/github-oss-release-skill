"""RED/GREEN tests for evidence-based badge assessment and validation."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
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


def write_readmes(root: Path, badges: list[str], english_badges: list[str] | None = None) -> None:
    english_badges = badges if english_badges is None else english_badges
    body = "# Example\n\nEvidence-first project.\n\n"
    (root / "README.md").write_text(body + "\n".join(badges) + "\n", encoding="utf-8")
    (root / "README.en.md").write_text(body + "\n".join(english_badges) + "\n", encoding="utf-8")


def badge(label: str, image: str, target: str) -> str:
    return f"[![{label}]({image})]({target})"


class BadgeAssessmentTests(unittest.TestCase):
    def assess(self, root: Path, metadata: dict | None = None) -> dict:
        module = load("assess_badges")
        return module.assess(root, "new-owner", "repo", "main", metadata=metadata or {})

    def validate(self, root: Path) -> dict:
        module = load("validate_badges")
        return module.validate(root, "new-owner", "repo", "main")

    # BADGE-RED-01: no workflow may not become a static CI claim.
    def test_static_ci_without_workflow_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [badge("CI", "https://img.shields.io/badge/CI-passing-brightgreen", "https://example.invalid/ci")])
            result = self.assess(root)
            self.assertTrue(result["broken_badges"])
            self.assertIn("BLOCKED_INVALID_EVIDENCE", {item["BADGE_EVIDENCE_STATUS"] for item in result["broken_badges"]})

    # BADGE-RED-02: no coverage service may not become a fabricated percentage.
    def test_static_coverage_without_source_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [badge("coverage", "https://img.shields.io/badge/coverage-95%25-brightgreen", "https://example.invalid/coverage")])
            result = self.assess(root)
            self.assertTrue(result["broken_badges"])
            self.assertIn("coverage", json.dumps(result, ensure_ascii=False).lower())

    # BADGE-RED-03: a license badge needs a license file or verified metadata.
    def test_license_without_evidence_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [badge("License", "https://img.shields.io/github/license/new-owner/repo", "https://github.com/new-owner/repo/blob/main/LICENSE")])
            result = self.assess(root)
            self.assertTrue(result["broken_badges"])

    # BADGE-RED-04: stale owner links are invalid even when the syntax is valid.
    def test_old_owner_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [badge("CI", "https://github.com/old-owner/repo/actions/workflows/ci.yml/badge.svg", "https://github.com/old-owner/repo/actions/workflows/ci.yml")])
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
            result = self.assess(root, {"workflow_runs": [{"workflow": "ci.yml", "conclusion": "success"}]})
            self.assertTrue(result["old_owner_badges"])

    # BADGE-RED-05: latest-release is not valid when no release exists.
    def test_release_without_release_record_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [badge("Release", "https://img.shields.io/github/v/release/new-owner/repo", "https://github.com/new-owner/repo/releases/latest")])
            result = self.assess(root)
            self.assertTrue(result["broken_badges"])

    # BADGE-RED-06: CodeQL badge needs both workflow and run evidence.
    def test_codeql_without_run_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "codeql.yml").write_text("name: CodeQL\n", encoding="utf-8")
            write_readmes(root, [badge("CodeQL", "https://github.com/new-owner/repo/actions/workflows/codeql.yml/badge.svg", "https://github.com/new-owner/repo/actions/workflows/codeql.yml")])
            result = self.assess(root)
            self.assertTrue(result["broken_badges"])

    # BADGE-RED-07: duplicate or excessive badges need a readability finding.
    def test_duplicate_badges_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            one = badge("License", "https://img.shields.io/github/license/new-owner/repo", "https://github.com/new-owner/repo/blob/main/LICENSE")
            write_readmes(root, [one] * 14)
            result = self.validate(root)
            self.assertTrue(result["duplicate_badges"])
            self.assertGreater(result["badge_count"], 6)

    # BADGE-RED-08: assessment is read-only and never creates a workflow.
    def test_assessment_performs_no_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            before = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assess(root)
            after = sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
            self.assertEqual(before, after)

    # BADGE-RED-09: README languages must carry the same badge facts.
    def test_bilingual_badges_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [badge("License", "https://img.shields.io/github/license/new-owner/repo", "https://github.com/new-owner/repo/blob/main/LICENSE")], [badge("Release", "https://img.shields.io/github/v/release/new-owner/repo", "https://github.com/new-owner/repo/releases/latest")])
            result = self.validate(root)
            self.assertFalse(result["valid"])
            self.assertTrue(result["bilingual_badges_match"] is False)

    # BADGE-RED-10: invalid URL and token query strings must fail closed.
    def test_badge_urls_reject_local_paths_and_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = "C:" + "/secret/badge.svg?token=hidden"
            target = "https://github.com/" + "new-owner" + "/repo"
            write_readmes(root, [badge("CI", image, target)])
            result = self.validate(root)
            self.assertFalse(result["valid"])
            self.assertTrue(result["findings"])

    def test_green_ci_license_release_and_python_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "ci.yml").write_text("name: CI\n", encoding="utf-8")
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nrequires-python = '>=3.11'\nversion = '1.2.3'\n", encoding="utf-8")
            write_readmes(root, [])
            result = self.assess(root, {"workflow_runs": [{"workflow": "ci.yml", "conclusion": "success"}], "release": {"tag_name": "v1.2.3"}})
            eligible = json.dumps(result["eligible_badges"])
            self.assertIn("CI", eligible)
            self.assertIn("License", eligible)
            self.assertIn("Release", eligible)
            self.assertIn("Python", eligible)

    def test_green_tag_without_release_prefers_tag(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [])
            result = self.assess(root, {"tags": ["v1.0.0"]})
            self.assertIn("Tag", json.dumps(result["eligible_badges"]))
            self.assertNotIn("Release", json.dumps(result["eligible_badges"]))

    def test_green_missing_coverage_requires_quality_setup(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [])
            result = self.assess(root)
            self.assertIn("Coverage", json.dumps(result["badges_requiring_setup"]))

    def test_green_codeql_and_dependency_audit_need_real_runs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".github" / "workflows").mkdir(parents=True)
            for name in ("codeql.yml", "dependency-audit.yml"):
                (root / ".github" / "workflows" / name).write_text("name: workflow\n", encoding="utf-8")
            write_readmes(root, [])
            result = self.assess(root, {"workflow_runs": [{"workflow": "codeql.yml", "conclusion": "success"}, {"workflow": "dependency-audit.yml", "conclusion": "success"}]})
            eligible = json.dumps(result["eligible_badges"])
            self.assertIn("CodeQL", eligible)
            self.assertIn("Dependency Audit", eligible)

    def test_green_private_repository_visibility_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_readmes(root, [])
            result = self.assess(root, {"visibility": "private"})
            self.assertIn("private", json.dumps(result, ensure_ascii=False).lower())

    def test_green_more_than_six_recommends_simplification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nrequires-python = '>=3.11'\nversion = '1.0.0'\n", encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            for name in ("ci.yml", "codeql.yml", "dependency-audit.yml"):
                (root / ".github" / "workflows" / name).write_text("name: workflow\n", encoding="utf-8")
            write_readmes(root, [])
            metadata = {"workflow_runs": [{"workflow": name, "conclusion": "success"} for name in ("ci.yml", "codeql.yml", "dependency-audit.yml")], "release": {"tag_name": "v1.0.0"}}
            result = self.assess(root, metadata)
            self.assertLessEqual(result["recommended_badge_count"], 6)
            self.assertTrue(result["simplification_advice"])


if __name__ == "__main__":
    unittest.main()
