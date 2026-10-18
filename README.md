# fireball_ai_toolkit
[![Tests](https://github.com/fireballenterprise/fireball_ai_toolkit/actions/workflows/tests.yml/badge.svg)](https://github.com/fireballenterprise/fireball_ai_toolkit/actions/workflows/tests.yml)

Single source of truth for the shared AI-agent tooling. Canonical agent
instructions and skills (a skill is a slash command) live here as tool-neutral markdown under
`fireball_ai_toolkit/content/`; each consuming repo mirrors that into `.fireball_ai_toolkit/` (its own
repo-specific additions live in `.<repo>/`). A generator renders every AI tool's native files
(`.claude/skills/`, `.github/skills/`, `.github/instructions/`, `.clinerules/`, `.sidecar/`, `AGENTS.md`)
from the `.fireball_ai_toolkit/` source: skills carry their full text, instructions are pointer stubs.

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
uv run --no-sync invoke ai_toolkit.migrate_skills  # fold a repo-local commands/ into skills/ (2.0.0); --dry-run to preview; apply runs it too
uv run --no-sync invoke ai_toolkit.mdfix       # normalise *.md (no blank after header, no stray ---); --check to gate
```
`download` / `upload` are kept as deprecated aliases for `apply` / `contribute`.
No dependency wanted (non-Python repo): `uvx --from git+https://github.com/fireballenterprise/fireball_ai_toolkit ai-toolkit apply`.

## Consuming-repo contract
| path | rule |
|------|------|
| `.fireball_ai_toolkit/` | clobbered copy of the toolkit's `content/` — never hand-edit |
| `.<repo>/` | this repo's own `instructions/ skills/` — never synced |
| `modules/fireball_ai_toolkit/`, `tasks/fireball_ai_toolkit/`, `tests/fireball_ai_toolkit/` | clobbered copies of `content/{modules,tasks,tests}/` — shared Python (`modules.fireball_ai_toolkit.*`) |
| `setup.sh`, `setup.ps1` | clobbered from `content/scripts/` — repo extras go in `setup.local.sh` (never clobbered) |
| `.claude/skills/`, `.github/{skills,instructions,copilot-instructions.md}`, `.clinerules/`, `.sidecar/instructions/`, `AGENTS.md`, `CLAUDE.md` | generated from `.fireball_ai_toolkit/` — never hand-edit |
| `.ai-toolkit.yml` (optional) | `vendor: [ai, scripts]` — take only some shipped trees (`ai`, `modules`, `tasks`, `tests`, `scripts`); absent = all |

Fix shared behavior by editing `content/` here, or by editing `.fireball_ai_toolkit/` in a consuming repo and
running `ai_toolkit.contribute` to open a PR.

## Skills are the slash commands
A **skill** is the one unit of AI behavior: the full text of a slash command, which a person calls as
`/<name>` or the AI loads on its own when the description matches. There is no separate `commands/`
layer (removed in 2.0.0).

**Why.** GitHub Copilot in VS Code moved to the Agent Skills runtime (same as Copilot CLI and the Copilot
app); `.github/prompts/` prompt files are no longer the way to expose a slash command. Claude Code already
treats skills as slash commands. One canonical skill therefore renders to both, and Sidecar reads it directly.

Canonical source, in `.fireball_ai_toolkit/skills/` (and a repo's own `.<repo>/skills/`):

* **flat** — `skills/<name>.md`: frontmatter + the full command text. Use this for almost everything.
* **bundle** — `skills/<name>/SKILL.md` (same frontmatter) plus any extra files (scripts, examples,
  templates) next to it. Use it only when a skill needs resources. Defining both `<name>.md` and `<name>/`
  is an error.

```yaml
---
description: Use for ... . Equivalent to /name.        # what it does + when the AI should load it
argument-hint: "[--repo <name|path>]"                  # shown after /name
hints:                                                 # optional extra trigger phrases
  - punch it
instructions:                                          # rule/skill files to read and follow
  - .fireball_ai_toolkit/instructions/git.md
user-invocable: false                                  # optional; omitted = true (person may call /name)
ai-invocable: false                                    # optional; omitted = true (AI may load it)
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.<module>.route "$ARGUMENTS"`
```

The two switches are optional in the canonical source (omitted = both on, Sidecar's default). The generated
`SKILL.md` always writes both keys out: `user-invocable: true|false` and
`disable-model-invocation: false|true` (`ai-invocable: false` -> `disable-model-invocation: true`).

Generated output: `.github/skills/<name>/SKILL.md` (Copilot) and `.claude/skills/<name>/SKILL.md` (Claude)
carry `name` (== folder), `description`, `argument-hint`, both switches, and the full body; a bundle's extra
files are copied alongside (dotfiles skipped, stale ones removed). Cline gets one workflow pointer per
user-invocable skill; `AGENTS.md` lists the skills as the slash commands. Sidecar needs no generated skill
files. Old generated `.github/prompts/`, `.claude/commands/`, `.sidecar/commands/` and `.sidecar/skills/`
files are deleted on the next render.

### Migrating a consuming repo (2.0.0)
```sh
uv run --no-sync invoke ai_toolkit.update
uv run --no-sync invoke ai_toolkit.migrate_skills --dry-run   # optional: preview the repo-local migration
uv run --no-sync invoke ai_toolkit.apply                      # runs migrate_skills itself, then renders
```
`migrate_skills` merges the repo's own `.<repo>/commands/<slug>.md` into `.<repo>/skills/<slug>.md`, deletes
the local `commands/`, rewrites `commands/` path references in the local docs to `skills/`, and lists
anything it cannot rewrite safely. A leftover `commands/` dir is still read for one release (with a
deprecation warning). See [CHANGELOG.md](CHANGELOG.md).

### Skill names (2.1.0)
The generated skill name and folder are always `[a-z0-9-]+` (lowercase; any run of other characters,
`_` included, becomes one `-`; leading/trailing `-` stripped; max 64 chars; name == folder). A source
`add_size_chart.md` renders as `add-size-chart` and keeps `add_size_chart` as a trigger phrase; two skills
that normalise to the same name are an error. `ai_toolkit.check` and `apply` fail on any generated skill whose
name/folder is outside `[a-z0-9-]+`, whose name differs from its folder or exceeds 64 chars, or whose
description exceeds 1024 chars. Why: Copilot's Agent Skills runtime silently drops invalid skills, whereas
the old prompt files allowed underscores (so `/add_bug` worked, then stopped loading after 2.0.0). The shipped
`add_bug` / `add_feature` / `add_task` are now `add-bug` / `add-feature` / `add-task`.

Consumer migration: `ai_toolkit.update`, then a SEPARATE `ai_toolkit.apply` (not `upgrade`: one process
would render with the old code), then rename repo-local underscore skills to hyphens (files and references).
`ai_toolkit.migrate_skills` is also `ai-toolkit migrate-skills`: the console script takes both spellings, while
the invoke task needs `auto_dash_names: true` for the hyphen form (this family sets it to false, so use the
underscore form with invoke). `migrate_skills` also treats a 1.x pointer-stub skill body ("Use this file as
source of truth: .github/prompts/<x>.prompt.md") as empty and merges the command body in.

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
