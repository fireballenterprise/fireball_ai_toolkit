---
name: pr-notes
description: Compare the current feature branch to its base branch (development/main) and draft a Pull Request description with a Summary and bulleted Changes.
argument-hint: no arguments required
agent: agent
---

Gather the branch and diff context:

!`uv run --no-sync python -m modules.toolkit.repo.route "pr_diff"`

If that fails, show the full output to the user and ask how they'd like to proceed.

Using the branch, commit log, and diff above, write a Pull Request description:
- `## Summary` — 1-3 sentences describing the overall change
- `## Changes` — a bulleted list of the key changes (one bullet per logical change, not per file)

Then:
- If you were invoked directly by the user (they typed `/pr-notes`), save the notes by running:
  `uv run --no-sync python -m modules.toolkit.repo.route "pr_notes --content=\"<the notes>\""`
  Report the saved file path to the user — they may copy/paste it into an existing PR description.
- If you are running as a step inside another command (e.g. `/pr` or `/punch-it-chewy`), do not
  save — just hold the composed notes so that command can use them directly.
