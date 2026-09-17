---
description: "Use when authoring a canonical slash command or instruction file (.fireball_ai_toolkit/toolkit/ via the toolkit, or a repo's .fireball_ai_toolkit/<repo>/) — the generator model, required frontmatter, and the thin-wrapper body."
applyTo: ".fireball_ai_toolkit/*/commands/**,.fireball_ai_toolkit/*/instructions/**,.claude/commands/**,.clinerules/workflows/**,.github/prompts/**,.sidecar/commands/**"
---
# AI Commands Instructions
Standards for the slash commands / custom prompts. **Commands are authored once** in
`fireball_ai_toolkit`'s `content/commands/*.md` (mirrored into each consuming repo as
`.fireball_ai_toolkit/toolkit/commands/`; repo-specific ones in `.fireball_ai_toolkit/<repo>/commands/`) and a generator renders one
pointer stub per tool. **Never hand-edit a generated provider file** — edit the `.fireball_ai_toolkit/` source and
re-run `invoke ai_toolkit.apply`.

## Architecture
Commands are the AI-facing entrypoint layer described in `.fireball_ai_toolkit/toolkit/instructions/logic.md` (Core Principle +
The Stack) — thin wrappers only, no business logic. See that file for why command bodies are the
AI's decision-capture layer, and how this differs from `.fireball_ai_toolkit/toolkit/instructions/tasks.md`'s plain CLI
automation.

## Canonical command file (`.fireball_ai_toolkit/toolkit/commands/<slug>.md`)
```yaml
---
name: <slug>
description: One line — what it does + when to use it
argument-hint: arg1 | arg2 [optional]      # or "no arguments required"
agent: agent
allowed-tools:                             # optional — only when the derived default is wrong
  - Bash(gh pr create *)
---

!`uv run --no-sync python -m modules.toolkit.<module>.route "$ARGUMENTS"`

<optional extra guidance for the agent — kept verbatim in every rendered view>
```

The `!` prefix runs bash; `$ARGUMENTS` receives everything after the command name. A command with
no `!` line is prose-only (the agent just follows the body).

## What the generator emits per tool
Every generated file is a **pointer stub**: provider frontmatter + one line
`Source of truth: .fireball_ai_toolkit/toolkit/commands/<slug>.md` (or `.fireball_ai_toolkit/<repo>/…`). No body is inlined.

| Tool | File | Frontmatter it still carries |
|------|------|------|
| GitHub Copilot | `.github/prompts/<slug>.prompt.md` | `name` + `description` + `argument-hint` + `agent` |
| Claude Code | `.claude/commands/<slug>.md` | `description` + `subtask: false` + `agent: general` + `slash_command: /<slug>` + a derived `allowed-tools` glob |
| Cline | `.clinerules/workflows/<slug>.md` | none (body-only file) |
| Fireball Sidecar | `.sidecar/commands/<slug>.md` | `name` + `description` + `argument-hint` + `agent` |

`allowed-tools` is still derived from the canonical `!` exec line (`uv run --no-sync …` →
`Bash(uv run --no-sync *)`, `AWS_PROFILE=X uv run …` → that plus the bare glob, `./setup.sh` →
`Bash(./setup.sh)`). Override it in canonical frontmatter only when that default is wrong.

## Creating a new command
1. Python module — `modules/<module>/<verb>.py` (ALL logic here) + `modules/<module>/route.py`
   (argument dispatch only). See `.fireball_ai_toolkit/toolkit/instructions/modules.md` for the router template.
2. `.fireball_ai_toolkit/toolkit/commands/<slug>.md` — the thin wrapper above.
3. `.fireball_ai_toolkit/toolkit/skills/<slug>.md` — the matching skill (see `.fireball_ai_toolkit/toolkit/instructions/ai_skills.md`).
4. `uv run --no-sync invoke ai_toolkit.apply` to regenerate, then `uv run --no-sync invoke fix` && `uv run --no-sync invoke
   test` (must be 10/10 for `.py` changes).

## Authoring instruction files (`.fireball_ai_toolkit/toolkit/instructions/<slug>.md`)
- One file per concern — the generated `AGENTS.md` index lists them all, derived from the bundle
- Always include a `description` in YAML frontmatter using the "Use when..." pattern
- Use an `applyTo` glob only when the instruction is relevant to a specific file type or directory
  (`**/*.py`, `**/*.csv`, `.github/workflows/**`); omit it (or `**`) for repo-wide rules
- Keep instructions actionable and example-driven — prefer short code blocks over prose
- No standalone `---` dividers in the body — see `.fireball_ai_toolkit/toolkit/instructions/markdown.md`

## Verbatim output blocks
A command whose job is to *show the user* an already-formatted answer (a Markdown table, a report)
should fence that answer so the Sidecar chat client renders it as-is instead of routing it through
the model for a paraphrase. Wrap it with `modules.common.utils.verbatim()`:

```python
from ..common.utils import verbatim

cli.echo(verbatim("\n".join(lines)))  # lines = the finished Markdown
```

This emits HTML-comment markers (`<!--sidecar:verbatim-->` … `<!--sidecar:/verbatim-->`) — invisible
in a plain terminal or any Markdown renderer that does not know the convention, so nothing is lost
for other consumers. Sidecar renders each fenced region as its own card in the transcript; when a
slash command's entire successful output is verbatim block(s) it also ends the turn with no cloud
round (zero tokens, no hallucination surface). Never fence `--json` / machine output. `backlog.list`
is the reference example.

## Targeting another repo (`--repo <name|path>`)
`fireball_orchestrator` runs the shared tooling against sibling repos it manages. `versioning.*`,
`tests.*`, `fix`, `test`, and `repo.{pull,push,cleanup,rebase,squash}` accept a target selector:

- **`--repo <name|path>`** anywhere in `$ARGUMENTS` — a `properties.yml` family-repo name, or a
  path to any git checkout (`--repo ../../levonbecker/dotfiles`).
- **`/update` and `/upgrade` also take a bare leading token** as the repo
  (`/update fireball_sidecar_android`) — resolved as a path when it looks like one (contains `/`
  or starts with `.` / `~` / `/`), else a family-repo name.
- Omitted → the current repo, behaviour unchanged.

A **name** only resolves where `properties.yml` has a `repos:` + `repos_local:` map (the
orchestrator); a **path** works anywhere; neither touches `properties.yml` in CI. Selection is
**entirely Python-side** — the VS Code extension just string-substitutes `$ARGUMENTS` into the
exec line and runs it in the open workspace, so the exec line stays `… route.py "$ARGUMENTS"` /
`invoke <task> $ARGUMENTS` and the router / task peels the selector. The work then runs as a
**fresh subprocess** in the target checkout (`cwd` + `$SIDECAR_REPO_ROOT`) —
`modules/toolkit/common/target_repo.py` — never in-process (the properties cache pins one process
to one repo). A check that's meaningless for the target (e.g. a Python-version check on a Kotlin
app) self-skips with a note (`modules/toolkit/common/toolchains.py`).

## uv --no-sync flag
Every `uv run` call in a command MUST use `--no-sync`:

```
✅ uv run --no-sync python -m modules.toolkit.chat.route "$ARGUMENTS"
❌ uv run python -m modules.toolkit.chat.route "$ARGUMENTS"
```

## Cache restart requirement
AI tools cache command files at startup. After an `apply` regenerates them, restart the AI tool
before testing.

## How a slash command routes
```
User: /chat resume wire_tunnels
  ↓  AI tool reads the rendered command file for its own format
  ↓  body executes: uv run --no-sync python -m modules.toolkit.chat.route "resume wire_tunnels"
  ↓  modules/toolkit/chat/route.py dispatches → modules.toolkit.chat.resume --pattern="wire_tunnels"
  ↓  the Python function receives pattern="wire_tunnels"
```
