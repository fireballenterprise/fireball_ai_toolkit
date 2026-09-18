# fireball_ai_toolkit
[![Tests](https://github.com/fireballenterprise/fireball_ai_toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/fireballenterprise/fireball_ai_toolkit/actions/workflows/tests.yml)

Single source of truth for the shared AI-agent tooling. Canonical slash commands, agent
instructions, and skills live here as tool-neutral markdown under
`fireball_ai_toolkit/content/`; each consuming repo mirrors that into `.fireball_ai_toolkit/` (its own
repo-specific additions live in `.<repo>/`). A generator renders a pointer stub for every AI tool
(`.claude/`, `.github/prompts/`, `.github/instructions/`, `.clinerules/`, `.sidecar/`, `AGENTS.md`)
back to the `.fireball_ai_toolkit/` source.

See [DESIGN.md](DESIGN.md) for the architecture, branch model, and open questions.

## Use it in a repo
```toml
# pyproject.toml — stable channel (floating major tag on main; @0 pre-1.0, @1 after launch)
[dependency-groups]
dev = ["fireball_ai_toolkit @ git+https://github.com/fireballenterprise/fireball_ai_toolkit@0"]
# dev channel: ...@development
```
```sh
uv run --no-sync invoke ai_toolkit.update      # uv lock --upgrade-package + uv sync (pull the newest release into the venv)
uv run --no-sync invoke ai_toolkit.apply       # clobber .fireball_ai_toolkit/ etc. from the installed package, regenerate
uv run --no-sync invoke ai_toolkit.upgrade     # update + apply — take the new toolkit in one step
uv run --no-sync invoke ai_toolkit.sync        # apply, but stop first if .fireball_ai_toolkit/ has local hand-edits
uv run --no-sync invoke ai_toolkit.contribute  # open a PR here with local .fireball_ai_toolkit/ changes
uv run --no-sync invoke ai_toolkit.check       # read-only drift gate (wire into invoke test / CI)
uv run --no-sync invoke ai_toolkit.mdfix       # normalise *.md (no blank after header, no stray ---); --check to gate
```
`download` / `upload` are kept as deprecated aliases for `apply` / `contribute`.
No dependency wanted (non-Python repo): `uvx --from git+https://github.com/fireballenterprise/fireball_ai_toolkit ai-toolkit apply`.

## Consuming-repo contract
| path | rule |
|------|------|
| `.fireball_ai_toolkit/` | clobbered copy of the toolkit's `content/` — never hand-edit |
| `.<repo>/` | this repo's own `instructions/ commands/ skills/` — never synced |
| `modules/fireball_ai_toolkit/`, `tasks/fireball_ai_toolkit/`, `tests/fireball_ai_toolkit/` | clobbered copies of `content/{modules,tasks,tests}/` — shared Python (`modules.fireball_ai_toolkit.*`) |
| `setup.sh`, `setup.ps1` | clobbered from `content/scripts/` — repo extras go in `setup.local.sh` (never clobbered) |
| `.claude/`, `.github/{prompts,instructions,skills,copilot-instructions.md}`, `.clinerules/`, `.sidecar/`, `AGENTS.md`, `CLAUDE.md` | generated pointer stubs → `.fireball_ai_toolkit/` — never hand-edit |
| `.ai-toolkit.yml` (optional) | `vendor: [ai, scripts]` — take only some shipped trees (`ai`, `modules`, `tasks`, `tests`, `scripts`); absent = all |

Fix shared behavior by editing `content/` here, or by editing `.fireball_ai_toolkit/` in a consuming repo and
running `ai_toolkit.contribute` to open a PR.

## Branch model
`development` (integration, PRs merge here) → promoted to `main` (stable) via
`ai_toolkit.release`, which tags a release. Consumers pin `@0` (stable, pre-1.0) → `@1` after launch or `@development`
(nightly). PyPI publishing (Trusted Publishing, no API token) is gated on the `PYPI_ENABLED` /
`TESTPYPI_ENABLED` repo variables — see `topics/ai_toolkit/plans/publish_on_pypi.md` in
`fireball_orchestrator` for the readiness checklist.

## Development
```sh
./setup.sh
uv run --no-sync invoke fix
uv run --no-sync invoke test
```
