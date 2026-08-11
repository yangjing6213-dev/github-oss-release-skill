# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses semantic version numbers for the Skill version recorded
in `SKILL.md`.

## [Unreleased]

## [2.1.0] - 2026-08-12

### Added

- Exact detection of changed GitHub Actions workflow paths.
- HTTPS OAuth/classic-PAT `workflow` scope preflight before repository creation
  or a workflow-file Push.
- Verification that scope evidence belongs to the credential source used by
  the planned Push.
- The independent `APPROVE_GITHUB_WORKFLOW_SCOPE_REFRESH` authorization.
- Workflow scope, credential source, protocol, and permission fields for local
  resume checkpoints.
- Simplified Chinese result handling for workflow-permission blocks.
- RED, GREEN, REFACTOR, resume, and ten workflow-scope scenario tests.
- Chinese and English prompt recipes for pre-publish audits, two-step initial
  publication, and two-step project updates.

### Changed

- Moved applicable workflow permission checks before remote repository
  creation and before project-update Pushes.
- Synchronized the Skill entry point, references, validators, fixtures, and
  scenario harness with version `2.1.0`.

## [2.0.0] - 2026-08-11

### Added

- Standalone open-source project files for Skill version `2.0.0`.
- MIT License with copyright held by ENHE AI Studio.

### Changed

- Classified publication quality gates according to the repository's actual
  directory-based Skill workflow and configured validators.
