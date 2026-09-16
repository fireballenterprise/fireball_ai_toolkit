---
description: "Use when authoring slash commands / instruction files / Python modules, or adding a provider — the modules/CLI/AI stack and the generator-based provider architecture."
applyTo: "**"
---
# Logic Architecture Instructions
## Core Principle
**All business logic lives in Python, in `modules/`, so it's testable. Everything else is a thin
CLI wrapper around it — and the AI is a decision-making wrapper on top of that CLI, not a fourth
code layer.**

## The Stack
```
modules/*/            All business logic. Reusable, testable. The only place anything
                       deterministic actually happens.
        ↑
        ├── modules/*/route.py   Thin dispatch, reached via slash commands. No logic.
        └── tasks/*.py (invoke)  Thin CLI wrapper too, reached via `invoke <task>`. Used for
                                  CI/CD-style automation (fix, test, sync, setup, upgrade)
                                  rather than interactive slash commands. No logic here either
                                  — see `.ai/toolkit/instructions/tasks.md`.
        ↑
An AI (or a human) calls either CLI — `python -m modules.toolkit.*.route` or `invoke <task>` — exactly
the way a human operator would from a terminal. Neither CLI knows or cares whether an AI or a
person is driving it.
```

- **Layer: Modules** (`modules/*/`) — ALL business logic, reusable, testable.
- **Layer: CLI wrappers** (`modules/*/route.py` for slash commands, `tasks/*.py` for `invoke`) —
  thin dispatch only, no business logic, no AI-specific behavior. Both are equally "just a CLI":
  deterministic, scriptable, runnable by a human or CI with zero AI involved.
- **Not a layer: the AI** — it's an intelligence/decision-making wrapper *on top of* the CLI
  above, not a layer inside it. It calls `route.py` or `invoke` exactly like a human user would,
  and makes some of the same judgment calls a human operator would (which options to pick, when
  to ask, when to stop). See below for where that judgment is captured.

## Running a Command
- Always prefix with **`uv run --no-sync`**: `uv run --no-sync invoke <task>` for an invoke task,
  `uv run --no-sync python -m modules.<x>.route "<args>"` for a slash-command module. `--no-sync`
  uses the project's `.venv` and does **not** re-resolve or update dependencies.
- **Never** run a bare `python3 -m ...`, `pip install --user` / `--break-system-packages`, or edit
  `PATH` to reach a task. That runs against the system interpreter, misses the `.venv`, and leaves
  packages installed outside the project. If `uv` itself isn't found, say so — don't work around it.
- A **`/slash-command`** (`/repo`, `/push`, `/backlog`, …) is not an executable — never type one
  into a terminal. Its behaviour is the `.ai/toolkit/commands/<name>.md` (or `.ai/<repo>/commands/`)
  body; the `` !`…` `` line there is the real command to run (the part *inside* the backticks, no
  leading `!`). Read that file, or run the underlying `route.py` / `invoke` directly.
- Pass a multi-word argument as **one quoted string**: `... repo.route "pull all"`, not
  `... repo.route pull all`.

## AI Is an Automated User, Not a Fourth Layer
The stack above is the entire runtime. An AI tool operates the CLI exactly the way a human would
type it at a terminal — there is no hidden AI-only code path, and no logic lives inside the AI
itself.

**Where the "intelligence" lives.** All dynamic, judgment-based decision-making an AI applies while
running a command — which options to pick, what to ask the user, when to stop, how to interpret
ambiguous input — is captured in the canonical command bodies (`fireball_ai_toolkit`'s
`content/commands/`, mirrored into each consuming repo as `.ai/toolkit/commands/`). Those bodies are
the single source of truth every AI tool reads for command *behavior* (see
`.ai/toolkit/instructions/ai_commands.md` for authoring them). If a decision isn't written down in a
command body or a standing rule under `.ai/toolkit/instructions/` (or `.ai/<repo>/instructions/`), an
AI enforcing it is not reproducible.

**The reproducibility test.** Before letting an AI make a judgment call inside a command, ask:
*could a human, or a CI script, make the same call by hand — reading the same
`.ai/toolkit/commands/<slug>.md` file and running the same
`uv run --no-sync python -m modules.toolkit.*.route "..."` / `invoke` commands — with zero AI involved?* If
yes, the design is correct: the AI is an automated user of a CLI that already fully works without
it. If no, the missing logic belongs in a command body (if it's judgment) or a Python module (if
it's deterministic) — never only in the AI's head.

**Why this matters — provider agnosticism.** Because judgment lives in command bodies and standing
rules live under `.ai/toolkit/instructions/`, no business logic and no decision logic is tied to any
specific AI model or vendor. Adding or swapping a provider (see below) never requires re-teaching
it anything new — it only needs to read the same `.ai/` files and call the same CLI, exactly like
every other provider already does.

## AI Provider Architecture
### Source of Truth
Shared rules, commands, and skills are authored once in **`fireball_ai_toolkit`'s `content/`**
and mirrored into each consuming repo as **`.ai/toolkit/`**; repo-specific ones live in
**`.ai/<repo>/`**. A generator renders both layers into every provider's native files.

**Every generated provider file is a pointer stub** — provider-specific frontmatter (`applyTo`,
`allowed-tools`, `name`, …) plus a single line back to `.ai/toolkit/<kind>/<slug>.md` (or
`.ai/<repo>/…`). No canonical body text is inlined anywhere. This includes Copilot's
`.github/instructions/*.instructions.md`: the `applyTo` glob still auto-applies the file, but what
it delivers is the pointer — the tool is expected to follow it to the `.ai/` source.

**Never hand-edit a generated provider file** (`.github/`, `.claude/`, `.clinerules/`, `.sidecar/`,
`AGENTS.md`, `CLAUDE.md`). Edit `.ai/toolkit/` (via the toolkit) or `.ai/<repo>/` and run
`invoke ai_toolkit.apply`; `invoke ai_toolkit.check` (inside `invoke test`) fails on
drift.

### Providers
| Provider | Reads | Notes |
|----------|-------|-------|
| **GitHub Copilot** | `.github/copilot-instructions.md` + `.github/instructions/*.instructions.md` (pointer stubs) | the `applyTo` glob auto-applies the stub; Copilot must follow the pointer to `.ai/toolkit/instructions/<slug>.md` |
| **Claude Code** | `CLAUDE.md` → `AGENTS.md` → `.ai/toolkit/ + .ai/<repo>/instructions/`; `.claude/commands/` + `.claude/skills/` (stubs → `.ai/`) | |
| **Fireball Sidecar** | `AGENTS.md` + `.sidecar/` stubs → `.ai/toolkit/ + .ai/<repo>/` | |
| **Codex / other AGENTS.md tools** | `AGENTS.md` → `.ai/toolkit/ + .ai/<repo>/instructions/` | |

### Adding or removing a provider
Add or remove a **renderer** in `fireball_ai_toolkit/renderers/` — not a hand-maintained
pointer file. The generator owns every provider dir.

## Documentation
- `.ai/toolkit/instructions/logic.md` — this file (stack + provider architecture)
- `.ai/toolkit/instructions/ai_commands.md` — canonical command / instruction authoring
- `.ai/toolkit/instructions/ai_skills.md` — skill file conventions
- `.ai/toolkit/instructions/tasks.md` — invoke task runner (plain CLI automation, no AI)
- `.ai/toolkit/instructions/modules.md` — Python module architecture and layout conventions
- `.ai/toolkit/instructions/tests.md` — testing requirements and workflow

Repo-specific instructions live in the consuming repo's `.ai/<repo>/instructions/` — the generated
`AGENTS.md` indexes the full merged set.
