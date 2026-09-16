---
description: "Use when setting up a repo for the first time, editing setup.sh / setup.local.sh, editing properties.yml, or working on the properties.yml bootstrap (modules/toolkit/setup/ + modules/setup/templates/)."
applyTo: "setup.sh,setup.ps1,setup.local.sh,setup.local.ps1,properties.yml,modules/setup/**,modules/toolkit/setup/**"
---
# Setup
## First-time setup
```sh
./setup.sh          # macOS / Linux
.\setup.ps1         # Windows (PowerShell)
```
Both install `uv` (user-local, no sudo/admin), run the repo-local hook, create `.venv`, `uv sync`,
then hand off to `uv run --no-sync invoke setup.properties` to write `properties.yml`.

## `setup.sh` / `setup.ps1` are clobbered
They come from `fireball_ai_toolkit` (`content/scripts/`) — `invoke ai_toolkit.apply`
overwrites them. **Never edit them.** Anything repo-specific goes in `setup.local.sh` /
`setup.local.ps1` (git-tracked, never clobbered). The base script sources it once and calls two
optional phase functions:
- `setup_local_tools` — after the OS tool install, **before** the venv (install extra tools here:
  Node, esbuild, …)
- `setup_local_post` — **after** `properties.yml` is written (things that read it: `invoke
  aws.cdk.ensure`, …)

```sh
# setup.local.sh — a repo that needs Node + a post-properties step
install_node_fnm() { ... }
setup_local_tools() { install_node_fnm; npm install --global esbuild; }
setup_local_post()  { uv run --no-sync invoke aws.cdk.ensure; }
```
PowerShell: `Setup-Local-Tools` / `Setup-Local-Post` in `setup.local.ps1`.

## `properties.yml` bootstrap (`modules/toolkit/setup/properties.py`)
- The `setup` module code is **shared** — clobbered into `modules/toolkit/setup/`. The tier YAML
  fragments are **repo-local** — kept in `modules/setup/templates/properties/*.yml` (never
  clobbered); `properties.py` reads them from there.
- Assembled once, on first run: one fragment per repo in the lineage
  (`template_python.yml` … `ai_vault.yml`), deep-merged; `repo.local`, `repo.remote`,
  `screenshots.location` stamped with detected values.
- A no-op every run after that — it only ever *creates* the file. To regenerate: delete
  `properties.yml` and re-run.
- Gitignored in `template_*` repos; the ignore line is stripped on first real setup so a scaffolded
  repo commits its `properties.yml`.

## `properties.yml` conventions
Keep the file skimmable — a maintainer should find a section from the editor's minimap/fold gutter
without scrolling.

- **Wrap every top-level section in fold markers:** a `# region <Name>` line immediately before
  the section's first key and a matching `# endregion <Name>` after its last line. One region per
  concern (`Repositories`, `AWS`, `Shopify`, `Versions`, `CloudFormation`, …). Editors fold on
  `# region` / `# endregion`, so this is the navigation index.
- **Comments are one line + a pointer, not an essay.** A section gets at most a single `#` line
  saying what it is and where the full explanation lives —
  `# Default AWS_PROFILE for aws/cdk shell-outs — see .ai/<repo>/instructions/aws.md`. Rationale,
  mechanism, and edge cases belong in that instruction doc, not woven into `properties.yml`.
- Per-key comments only for a genuinely non-obvious value; still one line.
