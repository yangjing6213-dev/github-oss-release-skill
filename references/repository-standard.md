# Repository standard

Inspect actual project needs; do not create ceremonial files or fictional
commands. Check, when applicable:

`README.md`, `README.en.md`, `LICENSE`, `CHANGELOG.md`, `CONTRIBUTING.md`,
`SECURITY.md`, `SUPPORT.md`, `CODE_OF_CONDUCT.md`, `AGENTS.md`,
`docs/REPOSITORY_STANDARD.md`, `.gitignore`, `.env.example`, and `.github/`.

The default bilingual convention is Simplified Chinese in `README.md` and
English in `README.en.md`, with accurate reciprocal links. Preserve an already
adopted, documented convention when changing an existing project. Never guess
a license or claim an unverified feature, badge, version, coverage value, or
maintenance promise.

Respect existing layouts such as `apps/`, `packages/`, `frontend/`, `backend/`,
`client/`, `server/`, `desktop/`, `api/`, `modules/`, and `services/`; do not
require `src/`. Match CI, issue/PR templates, Dependabot, ignore rules, and
entry points to the real stack. A CLI, library, SDK, API, data tool, or backend
usually records `VISUAL_ASSETS_REQUIRED = NO` unless its own user experience
requires assets.
