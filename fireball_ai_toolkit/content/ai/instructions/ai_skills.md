---
description: "Use when creating or editing a canonical skill file — .fireball_ai_toolkit/ + .<repo>/skills/ (flat <name>.md or <name>/SKILL.md bundle) and the SKILL.md files the generator renders from it."
applyTo: ".*/skills/**,.claude/skills/**,.github/skills/**"
---
# AI Skills Instructions
A **skill is the slash command** (`/<name>`) and also what the AI can load on its own. One canonical
file holds the full command text — there is no separate `commands/` layer (removed in toolkit 2.0.0).

## Canonical skill file (`.fireball_ai_toolkit/skills/<name>.md`)
Flat, one file per skill (repo-specific ones in `.<repo>/skills/<name>.md`):

```yaml
---
description: Use for ... . Equivalent to /<name>.   # what it does + when the AI should load it
argument-hint: "[--repo <name|path>]"                # optional
hints:                 # optional — extra natural-language trigger phrases
  - punch it
instructions:          # repo-relative paths to rule/skill files this skill pulls in
  - .fireball_ai_toolkit/instructions/git.md
user-invocable: false  # optional, default true — a person may call /<name>
ai-invocable: false    # optional, default true — the AI may call/auto-load it
---

!`uv run --no-sync python -m modules.fireball_ai_toolkit.<module>.route "$ARGUMENTS"`

Full behavior text the agent follows.
```

- The body is the whole command text (the `!` exec line plus judgment guidance). Keep it thin: logic
  lives in Python modules, rules in `instructions/`.
- `instructions:` is a list of **repo-relative paths**, written verbatim (`.fireball_ai_toolkit/…` for toolkit
  content, `.<repo>/…` for a repo's own). They are rendered into the body as a "read and follow" list.
- The two switches are optional; omitted = both true (Sidecar's default). The generator always writes
  both keys into `SKILL.md`: `user-invocable: true|false` and `disable-model-invocation: false|true`
  (`ai-invocable: false` renders as `disable-model-invocation: true`).
- An alias / sub-verb (`add_bug` → `backlog add bug`, `pr-notes`) is simply its own small skill.

## Bundle form for larger skills
A skill that needs resources (scripts, examples, templates) is a directory instead of a file:

```
skills/<name>/SKILL.md      same frontmatter + body as a flat skill
skills/<name>/scripts/…     any extra files, any depth
```

Having both `<name>.md` and `<name>/` is an error. Use the flat form unless the skill really has
resources. The generator copies the extra files next to the generated `SKILL.md` (relative paths kept,
dotfiles skipped) and removes resources that disappeared from the bundle.

## Rendered output (generated — never hand-edit)
| Location | Tool | Content |
|---|---|---|
| `.github/skills/<name>/SKILL.md` | GitHub Copilot (VS Code, CLI, app) | `name` + `description` + `argument-hint` + both switches; full body |
| `.claude/skills/<name>/SKILL.md` | Claude Code | same, plus derived `allowed-tools` |
| `.clinerules/workflows/<name>.md` | Cline | pointer to the canonical skill |
| (none) | Fireball Sidecar | reads `.fireball_ai_toolkit/skills/` and `.<repo>/skills/` directly |

Claude Code and Copilot reject unknown frontmatter keys, so `hints` and `instructions` are materialised
into the body, not carried as keys. `.github/prompts/` is no longer generated.

## Trigger phrases
Add a `hints:` entry (or spell the phrase out in `description`) for any trigger beyond the slash
name — e.g. `ship-it` also responds to "punch it" / "ship it". An implied phrase that is written down
nowhere is not discovered.

## Related
- `.fireball_ai_toolkit/instructions/ai_commands.md` — slash-command / instruction authoring
- `.fireball_ai_toolkit/instructions/logic.md` — overall AI/logic architecture
