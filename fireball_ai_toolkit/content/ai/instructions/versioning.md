---
description: "Use when working with the modules/toolkit/versioning/ package — bumping the repo's VERSION file for releases, or checking/updating dependency version locks, GitHub Actions action-ref pins, and .sdkmanrc toolchain pins."
applyTo: "modules/toolkit/versioning/**"
---
# Versioning Instructions
Everything lives under one namespace: **`versioning.*`** (short alias **`ver.*`** — `ver.check`
== `versioning.check`). The old names (`ver.libs`, `ver.update`, `ver.project_bump_*`, top-level
`upgrade`, `upgrade.python`) no longer exist.

## Project VERSION Bumps (`project.py`) — `versioning.bump`
The root `VERSION` file is the **single source of truth** for this repo's version — plain
`Major.Minor.Patch`, no build suffix, on `development` and `main`. `pyproject.toml` reads it via
`[tool.setuptools.dynamic]` (`version = { file = "VERSION" }`); never hand-write a `version =` in
`[project]`.

**Scheme (family-wide):**
- **Every merge to `development`** → `versioning.bump patch` (`0.2.0` → `0.2.1`). Automatic in
  dev→`main` CI repos (`version.yml`); a manual step elsewhere.
- **A release** just promotes `development` → `main` and tags the current `VERSION`. Force a
  milestone with the release workflow's `bump` input → `versioning.bump minor` / `major`.
- **Feature branches** may use `versioning.bump build` (`0.2.1` → `-001` → `-002`) as a local
  build counter — never merged or published.

```sh
uv run --no-sync invoke versioning.bump patch      # every merge to development
uv run --no-sync invoke versioning.bump minor      # milestone release
uv run --no-sync invoke versioning.bump major      # major release
uv run --no-sync invoke versioning.bump build      # feature-branch build counter, never published
```
All four only rewrite `VERSION` — no commit, branch, push, tag, or workflow trigger. `project.py`
has its **own** `get_repo_root()` keyed on `pyproject.toml` + `VERSION` — **not**
`setup.properties.get_repo_root()`, which searches for the git-ignored `properties.yml` (absent in
CI, where `version.yml` / `release.yml` run this). `setup.properties.get_repo_root()` also now
honours `$SIDECAR_REPO_ROOT`; `project.py`'s does not, deliberately.

## Version Checks (`check.py` → `libs.py`, `python.py`, `workflows.py`, `sdkman.py`)
`versioning.check` is **toolchain-aware**: with no sub-arg it runs only the checks the repo's
toolchains enable (via `modules/toolkit/common/toolchains.py`) — a Python library gets `libs` +
`python`, a repo with `.github/workflows/` gets `workflows`, a repo with a `.sdkmanrc` gets
`sdkman`. Name one to force just it. Each sub-check runs as its own subprocess; one exiting `3`
("nothing to do", including "no pyproject.toml") never stops the others.

- `libs` — `pyproject.toml` `[project.dependencies]` vs latest releases (`uv pip list --outdated`)
- `python` — pinned Python vs latest stable 3.x; rewrites config references (does not install)
- `workflows` — `.github/workflows/*.yml` `uses: owner/repo@vN` vs latest major tag on GitHub
- `sdkman` — `.sdkmanrc` toolchain pins vs `sdk list`; rewrites `.sdkmanrc` + the Gradle wrapper

```sh
uv run --no-sync invoke versioning.check                 # every applicable check
uv run --no-sync invoke versioning.check --only libs            # just one
uv run --no-sync invoke versioning.check --repo ../app   # against another checkout
uv run --no-sync invoke versioning.check --dry-run       # preview only
uv run --no-sync invoke versioning.check --yes           # skip prompts
uv run --no-sync invoke update                           # top-level alias for versioning.check
```
(`invoke` needs `--only <sub>` — an invoke positional can't be optional. The slash commands take
it bare: `/update libs`, via `versioning/route.py`.)

## Installs (`upgrade.py`) — `versioning.upgrade`
`check` rewrites the locks/pins; `upgrade` does the actual installs — the **binaries** (uv,
Python; the orchestrator fork adds cdk) **and** the libs (`uv sync --upgrade`) + the `.sdkmanrc`
toolchain.
```sh
uv run --no-sync invoke versioning.upgrade               # every applicable install (+ refresh uv)
uv run --no-sync invoke versioning.upgrade --only uv            # just the uv binary (brew / uv self update)
uv run --no-sync invoke versioning.upgrade --only python        # just Python + .venv rebuild
uv run --no-sync invoke versioning.upgrade --only libs          # just `uv sync --upgrade`
uv run --no-sync invoke versioning.upgrade --only sdkman        # just `sdk env install`
uv run --no-sync invoke versioning.upgrade --sync        # `uv sync --upgrade`, no version check
uv run --no-sync invoke upgrade                          # top-level alias
```
The `uv` binary is **unpinned** (always latest) — so `check` never touches it; only `upgrade`
refreshes it.
`/update [<repo>] [sub-check]` walks through applying the checks; `/upgrade [<repo>] [toolchain]`
runs the installs. Both take a leading `[<repo>]` or `--repo <name|path>`.

## `--repo` targeting
`versioning.check` / `.upgrade` take `--repo <name|path>` — a `properties.yml` family-repo name
(fireball_orchestrator only) or a path to any git checkout. The work runs as a fresh subprocess in
that checkout (`modules/toolkit/common/target_repo.py`). A check that's meaningless for the target
(e.g. `python` for a Kotlin app) self-skips with a note. `versioning.bump` takes only a path (a
bump is repo-local by definition) and is never given `--repo` in CI.

## Module Conventions
Same as `.ai/toolkit/instructions/modules.md` / `python.md`. See
`modules/toolkit/versioning/README.md` for per-file data-flow.
