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
uv run --no-sync invoke tests.style ruff         # just one (ruff | pylint | yamllint | actionlint | ktlint | detekt | android-lint | rustfmt | clippy | cargo-deny)
uv run --no-sync invoke tests.style --fix        # apply autofixes
uv run --no-sync invoke tests.unit               # every applicable unit runner
uv run --no-sync invoke tests.unit --scope versioning   # pytest marker subset (Rust: a cargo test-name filter)

# Another checkout
uv run --no-sync invoke test --repo ../other_repo
```

Do not run `uv run invoke ...` without `--no-sync`.

`tests.style` / `tests.unit` are **toolchain-aware** — they run only the tools the repo's
toolchains enable (Python repo → ruff/pylint/yamllint/actionlint/pytest; Kotlin/Gradle repo →
ktlint/detekt/android-lint/gradle-unit; Rust/Cargo repo → rustfmt/clippy/cargo-deny/cargo-test). A tool that isn't installed is reported **skipped**, not
failed. All logic is in `modules/fireball_ai_toolkit/tests/`; the tasks are thin wrappers.

## When to Run Tests
Run tests if you modified:
- `*.py` — any Python file (pylint + ruff)
- `*.yml` or `*.yaml` — any YAML file (yamllint)
- `.github/workflows/*.yml` — GitHub Actions (actionlint + yamllint)
- `*.rs`, `Cargo.toml`, `Cargo.lock` — Rust (rustfmt + clippy + cargo-deny + cargo test)

Skip tests for: `*.md`, config files, `*.toml`, `*.json`

## What Gets Tested (whatever the repo's toolchains enable)
- **ruff** / **pylint** — Python lint + format + code quality (Python repo)
- **yamllint** — YAML validation
- **actionlint** — GitHub Actions workflow validation
- **pytest** — the unit suite (must score 10/10)
- **ktlint** / **detekt** / **android-lint** / **gradle-unit** — Kotlin/Gradle repo
- **rustfmt** / **clippy** / **cargo-deny** / **cargo-test** — Rust/Cargo repo (see *Rust repos* below)
- **toolkit drift gate** + **mdfix** — run by `invoke test` in the current repo only

## Rust repos
A repo with a `Cargo.toml` is a Rust repo. Ruff's two jobs are split in Rust: **rustfmt** formats (`ruff format`) and
**clippy** lints (`ruff check`); naming rules are compiler warnings. The standard setup, as in Fireball Helix:

- `rust-toolchain.toml` — pinned stable channel with `components = ["clippy", "rustfmt"]`.
- `rustfmt.toml` — `edition`, `max_width = 100`, `use_field_init_shorthand = true`.
- `Cargo.toml` `[workspace.lints]` — `unsafe_code = "deny"` (one FFI crate may allow it), `missing_docs = "warn"`,
  `clippy::all = "warn"` plus the pedantic lints that catch real bugs (`float_cmp`, `needless_pass_by_value`, …);
  every crate takes `[lints] workspace = true`. `clippy.toml` for thresholds.
- `deny.toml` — allowed licences (no GPL/AGPL/LGPL), advisories, bans, sources; a non-default licence is a per-crate
  exception with the owner's decision noted, never a blanket allow.
- Gates: `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo deny check`,
  `cargo test --workspace --release` (always release). A repo's own full test task runs the lint gates first.
- CI: a `workflow_dispatch` workflow running the same four steps, kept current even when CI is off.

## Fix Issues — Never Disable Warnings
```python
# ❌ WRONG — never do this without asking user first
except Exception:  # pylint: disable=broad-exception-caught
    pass

# ✅ CORRECT — catch specific exceptions
except (ValueError, KeyError) as e:
    cli.echo(f"Error: {e}")
```
The same holds in Rust: fix the code a clippy lint points at; never `#[allow(...)]` it or loosen `[workspace.lints]`
without asking the user first.

If an issue is too complex to fix:
1. Try to fix it properly first
2. Ask the user — explain what the linter says and what you've tried
3. Wait for user approval before adding any exclusion
