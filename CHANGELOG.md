# Changelog
## 2.0.0
**Skills are the slash commands.** The separate `commands/` layer is gone.

Why: GitHub Copilot in VS Code moved to the Agent Skills runtime (same as Copilot CLI and the Copilot
app). A skill is invoked as `/<name>` or loaded by the AI; `.github/prompts/` is no longer how a slash
command is exposed. Claude Code already works this way.

Breaking changes
- `content/ai/commands/` removed. Each command body now lives in the same-named flat
  `skills/<slug>.md`; `add_bug`, `add_feature`, `add_task` and `pr-notes` became skills of their own.
- Skill frontmatter: `description`, `argument-hint`, `hints`, `instructions`, plus the optional
  `user-invocable` / `ai-invocable` switches (omitted = both true). The `commands:` key is gone.
- Larger skills may be a bundle: `skills/<slug>/SKILL.md` plus resource files.
- Generated output: `.github/skills/<slug>/SKILL.md` and `.claude/skills/<slug>/SKILL.md` carry the full
  text and always write `user-invocable` and `disable-model-invocation` explicitly. `.github/prompts/`,
  `.claude/commands/`, `.sidecar/commands/` and `.sidecar/skills/` are no longer generated and are deleted
  on the next render. Sidecar reads the canonical skills directly.
- `.github/copilot-instructions.md`, `AGENTS.md` and `CLAUDE.md` describe skills instead of prompts/commands.

Migration for a consuming repo
1. `uv run --no-sync invoke ai_toolkit.update`
2. `uv run --no-sync invoke ai_toolkit.migrate_skills --dry-run` (optional preview of the repo-local migration)
3. `uv run --no-sync invoke ai_toolkit.apply` (runs `migrate_skills` first when `.<repo>/commands/` exists, then
   renders). Review the "NOT rewritten" lines it prints and fix those references by hand.
4. Commit the result.

A leftover `commands/` directory is still read for one release with a deprecation warning, then ignored.
