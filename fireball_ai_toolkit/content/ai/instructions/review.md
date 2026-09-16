---
description: "Use when reviewing a pull request or code change in this repo — including automated PR review. Covers what to prioritize and what to skip."
---
# Review Instructions
## Priorities (in order)
1. **Logic correctness** — trace the actual code paths changed, don't just skim the PR
   description. Flag off-by-one errors, unhandled edge cases, incorrect conditionals, silent
   failures, and mismatched types. If a function's behavior changed, confirm every caller still
   gets what it expects.
2. **DRY / duplication** — flag near-duplicate logic that belongs in a shared helper (see
   `modules/toolkit/common/` in `.ai/toolkit/instructions/modules.md`), and duplicated
   constants/strings that should be defined once.
3. **Docs kept in sync** — if the diff touches a module, command, task, or config key, the
   matching `README.md` and the relevant instruction file must reflect it (see
   `.ai/toolkit/instructions/modules.md`). Canonical command/instruction/skill edits belong in
   `.ai/toolkit/` (via `fireball_ai_toolkit`'s `content/`) or `.ai/<repo>/`, never a generated
   provider file — see the consistency check below.
4. **Style compliance** — see `.ai/toolkit/instructions/markdown.md` (Markdown) and
   `.ai/toolkit/instructions/python.md` (Python style & ordering). Flag violations even
   where `invoke test` would still pass — some of these are conventions, not lint-enforced rules.
5. **Tests/linters** — see `.ai/toolkit/instructions/tests.md`. Any `.py`, `.yml`, or
   `.yaml` change must be clean under `uv run --no-sync invoke test` (pylint 10.00/10 required),
   and `uv run --no-sync invoke tests.pytest` must pass.

## Repo-Specific Consistency Checks
- `.ai/toolkit/` + `.ai/<repo>/` are the source of truth for all AI/agent rules — a PR that changes
  behavior without updating the relevant `.ai/` file is incomplete, not just under-documented.
- Commands/instructions/skills are authored once in `.ai/toolkit/` (via `fireball_ai_toolkit`'s
  `content/`) or `.ai/<repo>/` and rendered as pointer stubs into every provider dir
  (`.github/prompts/`, `.github/instructions/`, `.claude/`, `.clinerules/workflows/`, `.sidecar/`).
  Never hand-edit a generated provider file — flag a PR that does.
  `uv run --no-sync invoke ai_toolkit.check` confirms the generated files match
  `.ai/toolkit/` + `.ai/<repo>/`; it runs inside `invoke test`.

## What NOT to Flag
- Formatting nitpicks `ruff format` already enforces — don't re-litigate what the tool owns.
- Missing tests/lint conformance inside `topics/` — that content is excluded from this repo's own
  lint/test surface by design (see `extend-exclude`/`exclude` in `pyproject.toml`).
