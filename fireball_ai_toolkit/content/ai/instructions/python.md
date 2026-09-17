---
description: "Use when writing, editing, or reviewing Python code in this project. Covers Python version, style, ordering, comments, module conventions, and ruff/pylint configuration."
applyTo: "**/*.py"
---
# Python Instructions
## Python Version
Target: `>=3.14` (defined in `pyproject.toml`, pinned in `.python-version`)

## Style & Linting
- **Ruff** enforces fast style/lint checks — run `uv run --no-sync invoke tests.rufflint` to check, `uv run --no-sync invoke ruff.fix` to auto-correct
- **Pylint** is scoped to just `no-member` — the one check Ruff can't do (real type inference across installed
  deps to catch attribute/method access that doesn't exist on the inferred type). Everything else Pylint could
  flag is left to Ruff to avoid duplicate linting. Run `uv run --no-sync invoke tests.pylint` (must score 10.00/10
  to pass `invoke test` — see `[tool.pylint.messages_control]` in `pyproject.toml`)
- Run `uv run --no-sync invoke fix` to auto-correct everything Ruff can fix, then format
- Config lives in `pyproject.toml` under `[tool.ruff]` and `[tool.pylint]`
- Disable a rule inline only when necessary, with a comment explaining why:
  ```python
  value = compute()  # noqa: PLR0912 -- justified because ...
  ```

## Alphabetical Ordering
**Order functions, tasks, methods, and list items alphabetically** unless execution order requires otherwise (e.g., a pipeline that must run step 1 before step 2).

This applies to:
- Invoke task functions within a task file
- Module-level functions within a Python file
- Module-level constants (`UPPER_SNAKE_CASE`, PEP 8) within their file
- Dictionary keys, YAML keys, and list items where order is arbitrary
- Import groups are sorted by ruff — do not override

Insert a new item in its alphabetical position, and correct existing ordering when you're already
editing that file for another reason — not a mandate to resort files you aren't touching.

```python
# ✅ CORRECT — alphabetical
@task
def clean(...): ...

@task
def install(...): ...

@task
def restart(...): ...
```

```python
# ❌ WRONG — order of addition
@task
def install(...): ...

@task
def update(...): ...

@task
def clean(...): ...
```

## Module & File Conventions
- Use module-level functions (`def foo():`), not classes, unless state genuinely requires it
- Files under `modules/toolkit/common/` provide shared helpers (`cli`, `properties`, `utils`, `route_utils`)
- Every module reachable from a slash command exposes a `main()` entry point
- Use type hints on function signatures (`def foo(x: int) -> str:`)
- Prefer `pathlib.Path` over string paths

## Inline Code Comments
- Comment the *why*, not the *what*
- Reference external docs or issue numbers when a workaround is non-obvious
- Use `# noqa: RULE` or `# pylint: disable=rule-name` with an explanation comment on the same or preceding line

## Logging & Output
- Use `modules.toolkit.common.utils` helpers for all console output — `success()`, `error()`, `warning()`, `info()`
- Do not use `print()` directly in `modules/` code (tasks in `tasks/*.py` may `print()` for section headers)
- `error()` prints to stderr and exits the process — use for unrecoverable failures

## Shell Commands
- Use `subprocess.run([...], cwd=repo_path, check=...)` — always pass a list of args, never `shell=True`
- Never interpolate user input into shell strings

## Example Module Pattern
```python
"""One-line module docstring."""

from ..common import cli as click
from ..common.utils import success


def main() -> None:
    """Entry point for this module."""
    click.echo("Doing the thing...")
    success("Done")


if __name__ == "__main__":
    main()
```
