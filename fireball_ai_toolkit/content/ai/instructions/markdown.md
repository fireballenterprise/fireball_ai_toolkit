---
description: "Use when writing or editing any Markdown file. Covers headers, horizontal rules, verbosity, and README structure."
applyTo: "**/*.md"
---
# Markdown Style Standards
## Headers — NO blank line after a header
**MUST: never put a blank line after any header (`#`, `##`, `###`, …). The first line of content
comes immediately on the next line.** This is the opposite of the common default — do not follow
the habit. `uv run --no-sync invoke fix` (via `ai_toolkit.mdfix`) strips these automatically and `uv run --no-sync invoke test`
fails on them, but write them right the first time.

```markdown
✅ CORRECT
## Section
- bullet one
- bullet two

## Another Section
Content starts here immediately.
```

```markdown
❌ WRONG
## Section

- bullet one
```

Blank lines **before** a header (to separate sections) are fine and expected.

## Horizontal Rules
**Never use a standalone `---` line as a section divider in an instruction-file body**
(`.fireball_ai_toolkit/instructions/*.md`, `.<repo>/instructions/*.md`). The only `---` allowed there is
the YAML frontmatter fence (the opening and closing pair around `applyTo`). Headers and blank
lines are enough separation. `ai_toolkit.mdfix` removes stray dividers from instruction
files automatically.

## Verbosity
**When asked to create a file, keep it non-verbose unless the user says otherwise.** No preamble,
no restating the request, no filler explanation. Include only the substantive content. Add
structure, context, or commentary only when the user asks for it or the file's purpose requires it.

## README Files
- Lead with a short one-sentence description of the thing being documented
- The repo `README.md` includes: Setup, Project Structure, Invoke Tasks, and Modules sections
- Show invoke commands in fenced `sh` blocks (`uv run --no-sync invoke ...`)
- Keep it concise — link out rather than duplicating content that lives elsewhere

## Alphabetical Ordering
For code ordering rules (functions, invoke tasks, constants, dict/YAML keys), see
`.fireball_ai_toolkit/instructions/python.md`.
