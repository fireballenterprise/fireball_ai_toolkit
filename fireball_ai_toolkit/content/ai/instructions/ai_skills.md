---
description: "Use when creating or editing a canonical skill file — .ai/toolkit/ + .ai/<repo>/skills/<name>.md and the SKILL.md stubs the generator renders from it."
applyTo: ".ai/*/skills/**,.claude/skills/**,.github/skills/**,.sidecar/skills/**"
---
# AI Skills Instructions
## Canonical skill file (`.ai/toolkit/skills/<name>.md`)
A canonical skill is a **header only — no body**. Flat, one file per skill (repo-specific ones in
`.ai/<repo>/skills/<name>.md`):

```yaml
---
name: command_name
description: Use for ... . Equivalent to /command_name.
hints:                 # optional — extra natural-language trigger phrases
  - punch it
instructions:          # repo-relative paths to the rule files this skill pulls in
  - .ai/toolkit/instructions/git.md
commands:              # repo-relative paths to the command files this skill drives
  - .ai/toolkit/commands/command_name.md
---
```

A skill is pure wiring: trigger phrases (`description` + `hints`) plus pointers to the
`instructions` and `commands` that carry the actual "how". Never write prose or bash under the
frontmatter — if a skill needs to explain something, that belongs in one of its `instructions`
files.

- `instructions:` / `commands:` are lists of **repo-relative paths**, written verbatim
  (`.ai/toolkit/…` for toolkit content, `.ai/<repo>/…` for a repo's own).
- Every canonical command (`.ai/toolkit/commands/<slug>.md`) is wired to at least one skill —
  it appears in some skill's `commands:` list. Most commands have a same-named skill that lists
  itself; **alias / sub-verb commands ride on a parent skill instead** and get no skill of their
  own (`add_bug` / `add_feature` / `add_task` → `backlog`; `pr-notes` → `pr`). Bundle a command
  onto a parent skill only when it is the same *intent* as that skill (a phrasing, an alias, or an
  earlier stopping point) — distinct-effect operations keep their own skill.

## Rendered stubs (generated — never hand-edit)
| Location | Tool | Frontmatter | Body the generator writes |
|---|---|---|---|
| `.claude/skills/<name>/SKILL.md` | Claude Code | `name` + `description` only | pointer + **Trigger phrases** + **Instructions** / **Commands** lists |
| `.github/skills/<name>/SKILL.md` | GitHub Copilot (VS Code) | `name` + `description` only | same |
| `.sidecar/skills/<name>.md` | Fireball Sidecar | the whole canonical header (`name` + `description` + `hints` + `instructions` + `commands`) | pointer only |

Claude Code and Copilot reject unknown frontmatter keys, so their stubs carry only `name` +
`description` and everything else — the trigger phrases (as a **Trigger phrases** list) and the
`instructions:` / `commands:` paths — is materialised into the body. `.sidecar/` stubs are a
near-verbatim copy of the canonical header (Sidecar reads those keys straight off the
frontmatter). No canonical body text is inlined anywhere — there is none. The `<name>/SKILL.md`
directory shape is a rendered artifact Claude Code / Copilot require; the canonical source is
always the flat `.ai/…/skills/<name>.md`.

## Trigger phrases
Add a `hints:` entry (or spell the phrase out in `description`) for any trigger beyond the slash
name — e.g. `ship-it` also responds to "punch it" / "ship it". Every skill also gets its own
name spelled out (`_` / `-` → spaces) as a hint. An implied phrase that is written down nowhere
is not discovered.

Uses the Agent Skills open spec, but treat it as Claude Code-specific until other targeted tools
adopt it — hence `.claude/` rather than a vendor-neutral `.agents/`.

## Related
- `.ai/toolkit/instructions/ai_commands.md` — canonical command / instruction authoring
- `.ai/toolkit/instructions/logic.md` — overall AI/logic architecture
