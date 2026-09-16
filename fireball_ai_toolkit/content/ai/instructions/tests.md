---
description: "Use after changing any .py/.yml/.yaml file — the 10/10 golden rule, the fix-then-test workflow, and the never-disable-warnings policy."
applyTo: "**/*.py,**/*.yml,**/*.yaml"
---
# Testing Instructions
## Golden Rule
**IF YOU CHANGE `.py`, `.yml`, or `.yaml` FILES — YOU MUST GET 10/10 ON TESTS.**

No exceptions. No shortcuts.

## Workflow
```bash
# 1. Auto-fix first (ALWAYS do this before testing)
uv run --no-sync invoke fix

# 2. Run tests
uv run --no-sync invoke test
# Required: 10/10 score, exit code 0
```

## Canonical Commands (Use These Exactly)
```bash
# Full fix + full test
uv run --no-sync invoke fix
uv run --no-sync invoke test

# Targeted
uv run --no-sync invoke tests.style              # every applicable linter/formatter
uv run --no-sync invoke tests.style ruff         # just one (ruff | pylint | yamllint | actionlint | ktlint | detekt | android-lint)
uv run --no-sync invoke tests.style --fix        # apply autofixes
uv run --no-sync invoke tests.unit               # every applicable unit runner
uv run --no-sync invoke tests.unit --scope versioning   # pytest marker subset

# Another checkout
uv run --no-sync invoke test --repo ../other_repo
```

Do not run `uv run invoke ...` without `--no-sync`.

`tests.style` / `tests.unit` are **toolchain-aware** — they run only the tools the repo's
toolchains enable (Python repo → ruff/pylint/yamllint/actionlint/pytest; Kotlin/Gradle repo →
ktlint/detekt/android-lint/gradle-unit). A tool that isn't installed is reported **skipped**, not
failed. All logic is in `modules/toolkit/tests/`; the tasks are thin wrappers.

## When to Run Tests
Run tests if you modified:
- `*.py` — any Python file (pylint + ruff)
- `*.yml` or `*.yaml` — any YAML file (yamllint)
- `.github/workflows/*.yml` — GitHub Actions (actionlint + yamllint)

Skip tests for: `*.md`, config files, `*.toml`, `*.json`

## What Gets Tested (whatever the repo's toolchains enable)
- **ruff** / **pylint** — Python lint + format + code quality (Python repo)
- **yamllint** — YAML validation
- **actionlint** — GitHub Actions workflow validation
- **pytest** — the unit suite (must score 10/10)
- **ktlint** / **detekt** / **android-lint** / **gradle-unit** — Kotlin/Gradle repo
- **toolkit drift gate** + **mdfix** — run by `invoke test` in the current repo only

## Fix Issues — Never Disable Warnings
```python
# ❌ WRONG — never do this without asking user first
except Exception:  # pylint: disable=broad-exception-caught
    pass

# ✅ CORRECT — catch specific exceptions
except (ValueError, KeyError) as e:
    cli.echo(f"Error: {e}")
```

If an issue is too complex to fix:
1. Try to fix it properly first
2. Ask the user — explain what the linter says and what you've tried
3. Wait for user approval before adding any exclusion
