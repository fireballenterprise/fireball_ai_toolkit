---
description: "Use when working in topics/ — topic structure, chat-vs-docs rules, the research workflow, and the templates.py change rule."
applyTo: "topics/**"
---
# Topics Instructions
## Topic Structure
Topics live under `topics/` and nest to **any depth** — `topics/travel/`,
`topics/workshop/tig_welding/`, `topics/help/mac/vscode/` are all valid. A directory is a topic
when it holds an `AGENTS.md`; a directory that only groups deeper topics is not itself a topic.
Each topic directory contains:

```
topics/<path…>/
├── AGENTS.md      # AI agent instructions (cross-tool: Copilot, Codex, Sidecar, etc.)
├── CLAUDE.md      # thin pointer to AGENTS.md (Claude Code)
├── active.yml     # active chat tracker (git-ignored)
├── chats/         # AI conversation logs only (YYYYMMDD_title.md format)
├── plans/         # living design docs (YYYYMMDD_slug.md — see plans.instructions.md)
└── docs/          # user-facing files of any type (created on request)
```

The registry of every topic path is `topics/topics_list.yml` (`topics:` list + optional
`topic_meta:`). `/topic reindex` rebuilds it from the directories on disk — run it after a pull
that added or moved topics, or if `/topic switch` reports a topic "missing from the index". A
legacy `topics_layout:` nested tree is migrated to the flat `topics:` list automatically on first
read.

## Research Document Workflow — CRITICAL
**Default: Research stays in the chat file**
- All research and conversation belongs in the active chat: `chats/YYYYMMDD_title.md`
- **DO NOT automatically create separate research documents**
- Chat logs contain the complete conversation history

**Only create docs/ files when explicitly requested:**
- User says "create a doc with..." → create in `docs/category/filename.md`
- User says "make a domains.csv" → create `docs/domains.csv`
- User says "make a config.json" → create `docs/config.json`
- User does NOT ask for a file → keep everything in the chat file

## File Default Location Rule
**`docs/` = user-facing files of any type. `chats/` = AI conversation logs only.**

Any file the user asks to create goes in `docs/` by default — `.md`, `.csv`, `.txt`, `.json`, `.yml`, or any other type:
- User says "make a domains.csv" → `{active_topic_path}/docs/domains.csv`
- User says "create a headlights.md" → `{active_topic_path}/docs/headlights.md`
- User says "make a config.json" → `{active_topic_path}/docs/config.json`
- Exception: chat files always go in `chats/`; instruction files stay in their defined locations
- Exception: user explicitly specifies a different path → use that path

## File Management
- Work from git-tracked paths only (`topics/`, `agents/`)
- Use ISO 8601 date format: `YYYYMMDD_description.md` for chat files
- Screenshots stored centrally at repo root `screenshots/` — NOT in topic folders
- Never write files outside the repository root (`repo.local` in `properties.yml`) without explicit permission

## Instruction File Sync
When updating topic instructions in a topic directory:
- update `AGENTS.md` for topic-specific guidance
- keep `CLAUDE.md` as a thin pointer to the partner `AGENTS.md` in the same directory

Topic-specific guidance should live in `AGENTS.md`.

- `CLAUDE.md` should remain a thin pointer to `AGENTS.md`
- `CLAUDE.md` should not need content changes beyond pointing to the partner `AGENTS.md`
- Do not duplicate topic-specific rules in `CLAUDE.md`
- If topic guidance changes, update `AGENTS.md` as the content source of truth and keep `CLAUDE.md` as a pointer

## templates.py Change Rule — CRITICAL
`modules/toolkit/topic/templates.py` is the single source of truth for each topic's generated
`AGENTS.md`/`CLAUDE.md`. It drives what `/topic init` and `/topic update` produce.

**When you modify anything in `modules/toolkit/topic/` that affects topic instruction content:**
1. Run fix + test (10/10 required)
2. **Ask the user**: "Should I run `/topic update` to regenerate all topic AGENTS.md files with the new template?"
3. **Check root `AGENTS.md`** — it is hand-maintained and may need manual sync if the change reflects a new policy

This applies any time you touch `templates.py`, `init.py`, `update.py`, or any logic that affects what gets written to topic instruction files.

## Active State Files
- `active.yml` — tracks active chat in a topic (managed by chat scripts, git-ignored)
- `active_topic.yml` — tracks active topic at repo root (git-ignored)
