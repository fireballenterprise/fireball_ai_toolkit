---
description: "Use when creating, editing, or navigating Python code under modules/ — folder shape, mandatory CLI standards, path resolution, and the module template."
applyTo: "modules/**"
---
# Python Modules Instructions
All business logic lives here — slash commands and invoke tasks are thin CLI wrappers around it
(see `.ai/toolkit/instructions/logic.md`). Python style, ordering, and comment rules are in
`.ai/toolkit/instructions/python.md`; the 10/10 test gate is in `.ai/toolkit/instructions/tests.md`.

## Module Layout Consistency
Every folder under `modules/` follows the same shape so any module is navigable without reading
its source first:

- **`route.py`** — required in every module reachable from a slash command; dispatch only (router
  template below). Modules with no slash command may omit it.
- **`README.md`** — required in every module folder; documents the module's purpose and each file.
- **One file per verb/subcommand** — `chat/` has `start.py`, `end.py`, `list.py`, `resume.py`, not
  one large file. The filename matches the CLI subcommand exactly
  (`screenshots/configure.py` → `/screenshots configure`).
- **Naming** — directory names are lowercase `snake_case` nouns matching the domain/tool wrapped
  (`chat`, `repo`, `topic`, `versioning`) — never mixed case, never a `_module` suffix.
- **`common/`** is the only module importable from every other module — shared plumbing only, no
  domain logic.

## Mandatory Standards
### Named options only (no positional arguments)
```python
# ✅ CORRECT
@cli.command()
@cli.option("--title", default=None, help="Title for the chat")
def main(title: str | None = None):
    pass


# ❌ WRONG
def main(title):
    pass
```

### Path resolution
Always use `modules/toolkit/setup/properties.py` — never hardcode paths:
```python
from ..setup.properties import get_repo_local, get_screenshots_location

repo_root = get_repo_local()
```

### Inter-module imports
- `common/` utilities: importable from any module
- No cross-imports between domain modules (`chat/`, `topic/`, `repo/`, …) — if truly shared, move it to `common/`

## templates.py Change Rule
`modules/toolkit/topic/templates.py` is the single source of truth for each topic's generated `AGENTS.md`
/ `CLAUDE.md`. When you modify it, follow the **templates.py Change Rule** in
`.ai/toolkit/instructions/topics.md` (fix + test, ask about `/topic update`).

## Common CLI Option Patterns
```python
@cli.option("--title", default=None, help="...")            # optional string
@cli.option("--path", required=True, help="...")             # required string
@cli.option("--yes", "-y", is_flag=True, help="...")         # boolean flag
@cli.option("--count", default=20, help="...")               # int with default
@cli.option("--sort", type=cli.Choice(["newest", "oldest"]), default="newest")
@cli.option("--file", type=cli.Path(exists=True), help="...")
```
`modules.toolkit.common.cli` handles parsing, `--help` generation, type validation, defaults, and
user-friendly errors.

## Router Template
```python
# modules/<module>/route.py — argument dispatch only
import shlex, subprocess, sys
from modules.toolkit.common.route_utils import build_env, find_repo_root

_SUBCOMMAND_MODULES = {"start": "modules.toolkit.<module>.start", "end": "modules.toolkit.<module>.end"}


def main() -> int:
    raw = sys.argv[1:]
    args = shlex.split(raw[0]) if len(raw) == 1 else list(raw)  # accept "a b" or a b
    module = _SUBCOMMAND_MODULES.get(args[0]) if args else None
    if module is None:
        sys.stderr.write("Unknown subcommand\n")
        return 1
    repo_root = find_repo_root()
    cmd = [sys.executable, "-m", module, *args[1:]]
    return subprocess.run(cmd, cwd=repo_root, env=build_env(repo_root), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
```

### Retargeting to another repo (`--repo`)
A router for a verb that can act on *another* managed checkout (see `repo/route.py`,
`versioning/route.py`) adds a preamble right after `args = …`:

```python
from modules.toolkit.common.route_utils import peel_repo
from modules.toolkit.common.target_repo import delegate, resolve_target_repo

args, repo_token = peel_repo(args)
target = resolve_target_repo(repo_token)  # None / path / fuzzy family name
if target is not None:
    return delegate(target, f"<module>.{verb}", rest, caller_root=Path.cwd())
```

`resolve_target_repo` / `delegate` / `toolchains` are all in `modules/toolkit/common/` and stay
**stdlib-only at import** (CI-safe — `versioning.bump` runs in CI where `properties.yml` is
absent). Never switch repos in-process: `setup.properties` caches the repo root for the life of
the process, so `delegate` always spawns a fresh subprocess (`cwd` + `$SIDECAR_REPO_ROOT`).

## AI Provider Files
Commands, instructions, and skills are authored in `.ai/toolkit/` (via `fireball_ai_toolkit`'s
`content/`) or this repo's `.ai/<repo>/`, and rendered as pointer stubs into every provider dir by
`invoke ai_toolkit.apply`. There are no per-repo sync modules —
`invoke ai_toolkit.check` (inside `invoke test`) is the drift gate. See
`.ai/toolkit/instructions/ai_commands.md`.

## Module Template
```python
"""
Module description.

Usage:
    uv run --no-sync python -m modules.toolkit.<group>.<name> [--option value]
"""

from modules.toolkit.common import cli
from modules.toolkit.setup.properties import get_repo_local


@cli.command()
@cli.option("--argument", default=None, help="Description of argument")
def main(argument: str | None = None) -> None:
    """One-line summary of what this module does."""
    repo_root = get_repo_local()
    cli.echo(f"Repo root: {repo_root}")


if __name__ == "__main__":
    main()
```
