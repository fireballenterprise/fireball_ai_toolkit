---
name: test
description: Run every lint / unit check that applies to the repo (ruff, pylint, yamllint, actionlint, pytest; ktlint / detekt / gradle for Kotlin).
argument-hint: "[--repo <name|path>]"
agent: agent
---

Run all checks:

!`uv run --no-sync invoke test $ARGUMENTS`

`--repo <name|path>` runs the checks against another managed checkout. A tool that isn't installed
is reported *skipped*, not failed.

If all checks pass, report success and stop.

If any tests fail:
- For Ruff offenses: attempt to auto-fix by running `uv run --no-sync invoke fix`, then re-run `uv run --no-sync invoke test` to confirm. If offenses remain after auto-fix, show the remaining failures and ask the user how they would like to proceed.
- For Pylint offenses (must score 10.00/10): show the offending lines and ask the user how they would like to proceed.
- For YAML lint failures: show the offending lines and ask the user how they would like to proceed.
- For actionlint failures: show the offending workflow file and line, and ask the user how they would like to proceed.
- For any other failures: show the full error output and ask the user how they would like to approach fixing it.
