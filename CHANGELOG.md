# Changelog
## 2.1.0
**Skill names are normalised to `[a-z0-9-]+`.**

Why: Copilot's Agent Skills runtime silently drops a skill whose name is not lowercase letters, digits
and hyphens or does not equal its folder. The old prompt files allowed underscores, so `/add_bug` worked
before 2.0.0 and quietly stopped loading after the migration (fireball_ai_toolkit#107).

- Renamed `add_bug`, `add_feature`, `add_task` to `add-bug`, `add-feature`, `add-task`; the underscore
  spellings (and "add bug" etc.) stay as `hints:` trigger phrases. References in the backlog skill,
  rules and module README updated. The `!` command bodies are unchanged.
- The generated skill name and folder are always normalised: lowercase, any run of other characters
  (including `_`) becomes `-`, leading/trailing `-` stripped, max 64 chars, name == folder. If the source
  name differed (a repo-local `add_size_chart.md`), the original spelling is added to the skill's hints
  automatically. Two skills that normalise to the same name raise an error. The slash name shown by
  Sidecar, Claude and Copilot is the normalised one.
- `ai_toolkit.check` and `apply` fail with a clear message if any generated skill has a name or folder
  outside `[a-z0-9-]+`, a name different from its folder or longer than 64, or a description over 1024 chars.
- `ai-toolkit migrate-skills` also accepts `migrate_skills`. The invoke task is `ai_toolkit.migrate_skills`;
  the hyphen form works there only when invoke runs with `auto_dash_names: true`.
- `migrate_skills` treats a 1.x pointer-stub skill body (`Use this file as source of truth:
  .github/prompts/<x>.prompt.md`) as empty and merges the command body in (fireball_ai_toolkit#106).

Migration for a consuming repo
1. `uv run --no-sync invoke ai_toolkit.update`
2. In a SEPARATE command: `uv run --no-sync invoke ai_toolkit.apply` (not `upgrade`: one process would render
   with the old code).
3. Rename repo-local underscore skills to hyphens (files under `.<repo>/skills/` and every reference to them),
   then `apply` again.
4. Commit the result.

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
