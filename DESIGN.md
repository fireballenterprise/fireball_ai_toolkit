# fireball_ai_toolkit — Design
Single source of truth for the shared AI-agent tooling. Canonical slash commands, agent
instructions, and skills live here as tool-neutral markdown; a generator renders them into every
AI tool's native format inside each consuming repo.

Full project plan and history: `ai_vault` repo →
`topics/help/engineering/plans/consolidate_ai_toolkit.md`.

## Naming
| thing | value |
|-------|-------|
| GitHub repo | `fireballenterprise/fireball_ai_toolkit` |
| PyPI / dist name | `fireball_ai_toolkit` (unique, brand-scoped) |
| import package | `fireball_ai_toolkit` |
| invoke namespace | `ai_toolkit.{update,apply,upgrade,sync,contribute,check,release}` |
| console script | `ai-toolkit` (for the `uvx`, no-dependency path) |
| slash commands | n/a — invoke tasks + the `ai-toolkit` console script |

## Repository layout
```
fireball_ai_toolkit/        <- THE distributable package (the only thing in the wheel)
  content/                       <- everything shipped, as package data. apply clobber-copies:
    ai/{commands,instructions,skills}/*.md   -> .fireball_ai_toolkit/  (then rendered into every provider dir)
    modules/                                 -> modules/fireball_ai_toolkit/   (shared Python, modules.fireball_ai_toolkit.*)
    tasks/                                   -> tasks/fireball_ai_toolkit/
    tests/                                   -> tests/fireball_ai_toolkit/
    scripts/{setup.sh,setup.ps1}             -> repo root
  __init__.py       exposes __version__ (from importlib.metadata)
  cli.py            `ai-toolkit` console entrypoint
  catalog.py        parse content/ai/ (+ a repo's .<repo>/) -> ContentBundle; CLOBBER_TREES/FILES map
  render.py         run every renderer over the bundle
  renderers/        one per target: agents, claude, cline, copilot, prompts, sidecar
  apply.py         clobber every content/ tree into the repo, then render
  contribute.py    diff every clobbered path vs content/ -> PR against this repo
  sync.py          check clobbered paths -> stop on local edits -> apply
  check.py          read-only drift gate (every clobbered path + every rendered file)
  mdfix.py          normalise *.md house style (no blank after header; no stray --- in instructions)
  release.py        `gh workflow run release.yml`
modules/            <- the TOOLKIT's own dev tooling (NOT packaged): common/, setup/, versioning/.
                       A minimal subset — content/modules/fireball_ai_toolkit/ is the fuller consumer copy.
tasks/              <- toolkit's own invoke tasks (NOT packaged): ai_toolkit/, common/, tests/
VERSION             <- PEP 440 X.Y.Z; pyproject reads it via [tool.setuptools.dynamic]
MANIFEST.in         <- keeps the sdist in sync with the wheel
```
The parser module is `catalog.py`, not `content.py`, to avoid colliding with the `content/` data
directory. `modules/` and `tasks/` are excluded from the build by
`[tool.setuptools.packages.find] include = ["fireball_ai_toolkit*"]`.

## Branch model & channels
Both `main` and `development` are **PR-required** (ruleset "PR to Main + Development": `deletion` +
`non_fast_forward` blocked, `pull_request` required, 0 approvals; bypass actors = org admins and
the `fireball-actions-bot` App, `always`). `development` is the default branch.

* **`development`** — integration branch; feature PRs merge here. Every merge runs `version.yml`
  → `invoke ver.project_bump_patch` (`0.2.0` → `0.2.1`). Dev channel:
  `fireball_ai_toolkit @ git+https://github.com/fireballenterprise/fireball_ai_toolkit@development`
* **`main`** — stable; only updated by `release.yml` promoting `development` (via
  `ai_toolkit.release`). Default channel: pin the floating major tag — `@0` during pre-1.0,
  `@1` after the official launch. No `v` prefix.
* **Version scheme** (Levon: 0.x while pre-release, `1.0.0` = official launch):
  * `VERSION` is the single source of truth — plain PEP 440 `X.Y.Z`. `pyproject.toml` reads it via
    `[tool.setuptools.dynamic]` (`dynamic = ["version"]`), so there is nothing to keep in sync.
  * PR merge to `development` → `ver.project_bump_patch` (`0.2.0` → `0.2.1`).
  * Release → `ver.project_bump_minor` by default (`0.2.7` → `0.3.0`); the `release.yml` dispatch
    takes a `bump` input (`patch`/`minor`/`major`) — the official launch is `bump: major`
    (`0.x.y` → `1.0.0`).
  * `ver.project_bump_build` (`X.Y.Z-NNN`) stays for manual feature-branch use; nothing published
    ever carries a suffix.

### release.yml (`workflow_dispatch` with a `bump` input; `ai_toolkit.release` = `gh workflow run release.yml`)
Auth: `main` + `development` are PR-required (public repo, ruleset enforced). The org-wide
**`fireball-actions-bot`** App (`vars.BOT_APP_ID` + `secrets.BOT_PRIVATE_KEY`, via
`actions/create-github-app-token@v3`) is a bypass actor — every job that pushes uses its token.
Jobs:
1. **version** — `invoke ver.project_bump_${{ inputs.bump }}`; advance the patch if the candidate
   tag is taken; commit `chore: release X.Y.Z [skip ci]`; push `development`.
2. **promote** — `git merge origin/development --no-ff -X theirs` onto `main`; push.
3. **tag** — `git tag X.Y.Z` + `git tag -f X` (floating major); push both. **No `v` prefix.**
   `git ls-remote --tags` guard so re-runs are safe.
4. **publish_release** — `gh release create X.Y.Z --target main --generate-notes`.
5. **pypi** — gated on repo variable `PYPI_ENABLED == 'true'`. `uv build` + `pypa/gh-action-pypi-
   publish` via **Trusted Publishing / OIDC** (`id-token: write`, no API token).

### Two publish channels (mirrors the app repos' dev/prd deploy split)
| channel | trigger | index | gate | environment |
|---------|---------|-------|------|-------------|
| **TestPyPI** | every merge to `development` (`version.yml` `publish_testpypi` job) | test.pypi.org | `vars.TESTPYPI_ENABLED` | `testpypi` |
| **PyPI** | `release.yml` (main promotion) | pypi.org | `vars.PYPI_ENABLED` | `pypi` |

TestPyPI is the practice loop — publish on every dev merge, then a consuming repo installs from it
(`uv pip install --index-url https://test.pypi.org/simple/ fireball_ai_toolkit`, or a
`[[tool.uv.index]]` entry) to exercise the full round trip before the real `1.0.0`. Each needs its
own **Trusted Publisher** configured on the respective site (repo + workflow filename +
environment name); the two are independent. Versions are immutable on both — `skip-existing: true`
keeps re-runs safe.

## Distribution
Each consuming repo adds a dev dependency (default = stable):
```toml
[dependency-groups]
dev = ["fireball_ai_toolkit @ git+https://github.com/fireballenterprise/fireball_ai_toolkit@0"]
```
`uv.lock` captures the exact commit; updates are deliberate
(`uv lock --upgrade-package fireball_ai_toolkit`). The wheel bundles `content/` as package
data, so `apply` clobbers every managed path straight from the install — no network, no Copier,
no submodule. Non-Python / day-job repo:
`uvx --from git+https://github.com/fireballenterprise/fireball_ai_toolkit ai-toolkit apply`.

## Consuming-repo contract
```
.fireball_ai_toolkit/     clobbered copy of content/ai/ — NEVER hand-edited
modules/fireball_ai_toolkit/ clobbered copy of content/modules/ — shared Python, imported as modules.fireball_ai_toolkit.*
tasks/fireball_ai_toolkit/   clobbered copy of content/tasks/
tests/fireball_ai_toolkit/   clobbered copy of content/tests/
setup.sh setup.ps1   clobbered from content/scripts/ — repo extras go in setup.local.sh (not clobbered)
.<repo>/      this repo's own instructions/ commands/ skills/ (e.g. .fireball_ai_vault/) — never synced
modules/ tasks/ tests/ (root)   this repo's own code — never touched
<generated> .claude/ .github/{prompts,instructions,skills,copilot-instructions.md} .clinerules/
            .sidecar/ AGENTS.md CLAUDE.md — NEVER hand-edited; each file is a pointer stub back
            to .fireball_ai_toolkit/ or .<repo>/ (provider frontmatter + one "Source of truth:" line)
```
- `ai_toolkit.apply` — clobber every managed path from the package, render every provider
  stub (with `.<repo>/` layered on top).
- **Partial vendoring** — `.ai-toolkit.yml` at the repo root, `vendor: [ai, scripts]`, limits
  which shipped trees a repo takes (`ai`, `modules`, `tasks`, `tests`, `scripts`; absent file =
  all of them). For a repo whose shared Python has diverged too far to clobber: take `.fireball_ai_toolkit/` +
  `setup.sh` now, reconcile the rest into `content/` over time, then widen the list. `apply` /
  `check` / `sync` / `contribute` all honour it; without `ai` in the list the render step is skipped.
- `ai_toolkit.contribute` — diff every managed path vs `content/`, open a PR against this repo
  (refuses edits outside the managed set, and `.<repo>/` / generated output).
- `ai_toolkit.sync` — check the managed paths for uncommitted edits -> surface them and ask
  whether to contribute first -> then apply -> render. What `/toolkit_sync` and the skill call.
- `ai_toolkit.check` — read-only drift gate for `invoke fix` / `invoke test` and CI.
- `ai_toolkit.mdfix` — normalise every `*.md` to the house style (`invoke fix` writes,
  `invoke test` runs `--check`). Enforces the rules AI tools keep dropping mid-generation.
- `ai_toolkit.release` — (toolkit repo, and a convenience wrapper elsewhere) promote
  `development` -> `main` and cut a tag.

## Open design questions
1. **Shared vs local content split.** The initial port copied *all* of ai_vault's
   `.github/instructions/` and `.github/prompts/`. See the plan's Shared-vs-Local table for the
   agreed division. ai_vault-specific files move to `.<repo>/` before the first real `apply`.
2. **`.<repo>/` merge semantics** — additive-only, or per-file override of an `.fireball_ai_toolkit/` file?
3. **Circular dependency** — this repo is scaffolded from `template_python`; once `template_python`
   also consumes the toolkit, keep the toolkit free of its own dependency (it *is* the source) and
   render its own provider views from its own `content/`.
4. **Exec-line rewriting** — canonical command bodies use
   `!`uv run --no-sync python -m modules.<x>.route`. Consuming repos may need a different module
   path prefix; the renderer may need a token the repo substitutes.
5. ~~**Slash-command names** — `/toolkit_*` vs `/devkit_*` vs `/sidecar_*` (the last collides with
   the Sidecar product name).~~ Resolved by the `fireball_sidecar_toolkit` → `fireball_ai_toolkit`
   rename (repo, package, CLI, and invoke namespace all dropped the `sidecar` prefix) — the
   toolkit is generic AI-agent tooling, not part of the Sidecar product line.
6. **Shared release wrapper** — item 3 from the chat: ship `ai_toolkit.release` (and
   `.contribute`) as part of the toolkit's own shared task set so every repo can
   `ai_toolkit.contribute && ai_toolkit.release` easily.
