---
description: "Use when adding or editing an invoke task, or looking up the command for fix / test / upgrade / versioning / toolkit sync."
applyTo: "tasks/**"
---
# Tasks Instructions
Invoke is the task runner for CI/CD-style automation (fix, test, upgrade, version checks). Tasks
live in `tasks/` and run via `uv run --no-sync invoke <task>` (always `--no-sync`). **Never put
business logic in a task — that lives in `modules/`.** An invoke task is a thin wrapper that
translates kwargs to CLI flags and shells to `python -m modules.fireball_ai_toolkit.<pkg>.<verb>`; anything
with branching, discovery, or I/O belongs in the module. `tasks/fireball_ai_toolkit/` is one file per
`modules/fireball_ai_toolkit/<pkg>` package, same name (`versioning.py`, `tests.py`, `repo.py`, …).

## Most-Used
```bash
uv run --no-sync invoke fix    # every applicable autofixer (ruff --fix + format, ktlint format, …)
uv run --no-sync invoke test   # every applicable lint + unit check + toolkit drift gate
```

## `--repo <name|path>` (target another checkout)
`versioning.*`, `tests.*`, `fix`, `test`, `repo.{pull,push,cleanup,rebase,squash}`, and
`setup.properties` take `--repo <name|path>` — a `properties.yml` family-repo name, or a path to
any git checkout. Default (omitted) = the current repo, unchanged. Only works where a
`repos:`/`repos_local:` map exists (fireball_orchestrator) for the *name* form; the *path* form
works anywhere. Implemented in `modules/fireball_ai_toolkit/common/target_repo.py` (fresh subprocess in the
target — never in-process).

## Task Groups
| Group | Tasks |
|---|---|
| `tests.*` | `style` (every applicable linter/formatter; `--fix`, `--only`), `unit` (pytest / gradle-unit; `--scope`) |
| `versioning.*` (alias `ver.*`) | `check [libs\|python\|workflows\|sdkman]` (toolchain-aware; was `ver.update` / `ver.libs` / …), `upgrade [uv\|python\|libs\|sdkman]` / `--sync` (installs — bins + libs; was top-level `upgrade` + `uv.*`), `bump {patch\|minor\|major\|build}` (was `ver.project_bump_*`) |
| top-level | `fix`, `test`, `update` (= `versioning.check`), `upgrade` (= `versioning.upgrade`) |
| `ai_toolkit.*` | `update`, `apply`, `upgrade`, `sync`, `contribute`, `check` — shipped by the `fireball_ai_toolkit` package (see below) |

`versioning.check` only rewrites locks (`pyproject.toml`, `.github/workflows/`, `.sdkmanrc`) —
it doesn't install; `versioning.upgrade` does. `--dry-run` / `--yes` on `check`.

## AI Provider Sync (`ai_toolkit.*`)
Shared commands / instructions / skills come from `fireball_ai_toolkit`. The tasks are shipped
by the package and mounted under `ai_toolkit.*`:

| Task | Description |
|---|---|
| `update` | pull the newest toolkit release into the venv (`uv lock --upgrade-package` + `uv sync`) — nothing in the repo tree changes yet |
| `apply` | clobber `.fireball_ai_toolkit/` + `modules/fireball_ai_toolkit/` + … from the **installed** package, regenerate every provider stub |
| `upgrade` | `update` then `apply` — take the new toolkit into this repo in one step |
| `sync` | `apply`, but stop first if `.fireball_ai_toolkit/` has local hand-edits (offer to `contribute` them) |
| `contribute` | open a PR against the toolkit with local `.fireball_ai_toolkit/` edits |
| `check` | read-only drift gate (runs inside `invoke test`) |
| `mdfix` | normalise every `*.md` (no blank after a header; no stray `---` in instruction bodies). `invoke fix` writes it, `invoke test` runs `mdfix --check` |

`download` / `upload` are kept as deprecated aliases for `apply` / `contribute`.

Never hand-edit a generated provider file. See `.fireball_ai_toolkit/instructions/ai_commands.md`.

## Conventions
- Tasks within a file are ordered **alphabetically by function name** — not by date or grouping
- `tasks/__init__.py` builds the root `Collection` — all task modules are wired explicitly, no
  auto-glob loading
- `modules/` are plain importable packages, imported directly by `tasks/*.py`
