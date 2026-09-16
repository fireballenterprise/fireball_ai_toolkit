---
name: update
description: Check pyproject.toml dependencies, the pinned Python version, .github/workflows/ action refs, and .sdkmanrc toolchain pins against their latest published releases and update the locks. Does not install or run anything.
argument-hint: "[<repo>] [libs | python | workflows | sdkman] [--repo <name|path>]"
agent: agent
---

Check for available version updates (read-only, makes no changes):

!`uv run --no-sync python -m modules.toolkit.versioning.route "check $ARGUMENTS --dry-run"`

The check is **toolchain-aware** — it runs only the sub-checks the repo actually has: a Python
library gets the `pyproject.toml` dependency table and the Python-version table; a repo with
`.github/workflows/` gets the action-ref table; a repo with a `.sdkmanrc` gets the toolchain
table. Any section may say it's already up to date — treat that section as done.

## Targeting another repo
`$ARGUMENTS` may start with a repo selector — a family-repo name (`/update fireball_sidecar_android`)
or a path (`/update ../../levonbecker/dotfiles`), or `--repo <name|path>` anywhere. With one, the
check runs against that checkout instead of the current one. No selector → the current repo.

## Which section(s) to act on
- a sub-check name (`libs` / `python` / `workflows` / `sdkman`) → act only on that section.
- no sub-check name → walk through every section the check printed.

## Applying an update
Show the user the relevant table exactly as printed, then ask whether to apply it. On yes, re-run
the same command **without `--dry-run` and with `--yes`**, scoped to that section — e.g.

!`uv run --no-sync python -m modules.toolkit.versioning.route "check libs --yes"`

then tell them what was rewritten:
- `libs` — only version constraints in `pyproject.toml`; `/upgrade libs` installs them.
- `python` — only config references; `/upgrade python` installs the new Python + rebuilds `.venv`.
- `workflows` — only `@ref` pins; suggest reviewing the diff before committing.
- `sdkman` — only `.sdkmanrc` + the Gradle wrapper; `/upgrade sdkman` runs `sdk env install`.

If the user declines a section, make no changes for it.
