# Versioning Module
Checks project version configs against the latest published releases and updates the locks —
it does not install anything or run any workflow. Installing is a separate, explicit step
(`/upgrade` / `invoke versioning.upgrade`). Also bumps the repo's root `VERSION` file for
development deploys and releases (`project.py`).

Every check is **toolchain-aware** (`modules/toolkit/common/toolchains.py`): `versioning.check`
with no sub-arg runs only the checks whose toolchain the repo actually has — a Python library
gets `libs` + `python`, a repo with `.github/workflows/` gets `workflows`, a repo with a
`.sdkmanrc` gets `sdkman`. This is what lets `--repo <name|path>` point any check at another repo.

## Usage
```sh
uv run --no-sync invoke versioning.check                 # every applicable check (was ver.update)
uv run --no-sync invoke versioning.check --only libs            # just the dependency-lock check
uv run --no-sync invoke versioning.check --repo ../app   # run the applicable checks in another checkout
uv run --no-sync invoke versioning.check --dry-run       # preview only, never writes
uv run --no-sync invoke versioning.check --yes           # skip confirmation prompts
uv run --no-sync invoke update                           # top-level alias for versioning.check
uv run --no-sync invoke ver.check                        # short alias for versioning.*

uv run --no-sync invoke versioning.upgrade               # install every applicable upgrade (+ refresh uv)
uv run --no-sync invoke versioning.upgrade --only uv            # just the uv binary
uv run --no-sync invoke versioning.upgrade --only python        # just Python + .venv rebuild
uv run --no-sync invoke versioning.upgrade --sync        # just `uv sync --upgrade`
uv run --no-sync invoke upgrade                          # top-level alias for versioning.upgrade

uv run --no-sync invoke versioning.bump patch            # every merge to development (X.Y.Z -> X.Y.Z+1)
uv run --no-sync invoke versioning.bump minor            # milestone release
uv run --no-sync invoke versioning.bump major            # major release
uv run --no-sync invoke versioning.bump build            # feature-branch build counter, never published
```

`/update` and `/upgrade` are the slash commands; both accept a leading `[<repo>]` or
`--repo <name|path>` (see `.ai/toolkit/instructions/versioning.md`).

## Files
- `check.py` — the orchestrator behind `/update` / `versioning.check`: picks the applicable
  sub-checks via `common.toolchains`, runs each as its own subprocess (one exiting `3` = "nothing
  to do" never stops the others), fails only on a real error
- `route.py` — `/update` / `/upgrade` router: peels the `--repo` / bare-repo selector, maps the
  positional sub-arg to `--only`, delegates into the target checkout or runs local
- `libs.py` — checks `[project.dependencies]` / `[project.optional-dependencies]` against
  `uv pip list --outdated`, rewrites the locks preserving constraint operators (exits `3` when
  up to date, or when there's no `pyproject.toml`)
- `python.py` — checks the pinned Python version against the latest release, rewrites config
  references (exits `3` when up to date or no `pyproject.toml`)
- `workflows.py` — scans `.github/workflows/*.yml` `uses: owner/repo@vN` refs against the highest
  published major tag (`git ls-remote`, no API token), rewrites the pins in place
- `sdkman.py` — checks `.sdkmanrc` toolchain pins (JDK/Gradle/Kotlin) against `sdk list`, rewrites
  `.sdkmanrc` + the Gradle wrapper (exits `3` when there's no `.sdkmanrc`)
- `upgrade.py` — the installs behind `/upgrade`: the `uv` binary (`brew upgrade uv` / `uv self
  update` — unpinned), the pinned Python + `.venv` rebuild, `uv sync --upgrade`, `sdk env install`.
  `--only uv|python|libs|sdkman`, `--sync`
- `project.py` — bumps the root `VERSION` file. Has its **own** `get_repo_root()` (keyed on
  `pyproject.toml` + `VERSION`, **not** `properties.yml`) so it works in CI. Does not commit,
  push, or trigger any workflow.

`libs.py`, `python.py`, `workflows.py`, `sdkman.py`, `project.py` only edit files — review the
diff before committing.
