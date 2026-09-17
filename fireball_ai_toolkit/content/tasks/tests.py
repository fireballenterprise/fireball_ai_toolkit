"""Thin wrappers over ``modules.toolkit.tests`` — ``style`` (lint + format) and ``unit``.

All discovery / per-tool logic is in the module. ``fix`` / ``test`` in ``main.py`` call these.
"""

from invoke import Collection, task

from ._targets import with_target

_STYLE = "tests.style"
_UNIT = "tests.unit"


@task(
    help={
        "only": "Run one linter: ruff | pylint | yamllint | actionlint | ktlint | detekt | android-lint",
        "fix": "Apply autofixes where the tool supports it (ruff, ktlint)",
        "repo": "Lint another checkout — a family-repo name or a path",
    }
)
def style(context, only=None, fix=False, repo=None):
    """Run every applicable linter / formatter (toolchain-aware)."""
    args: list[str] = []
    if only:
        args += ["--only", only]
    if fix:
        args.append("--fix")
    if with_target(repo, _STYLE, args):
        return
    context.run(f"python -m modules.toolkit.{_STYLE} {' '.join(args)}".rstrip())


@task(
    help={
        "only": "Run one runner: pytest | gradle-unit",
        "scope": "pytest marker expression, e.g. versioning (pytest only)",
        "repo": "Run another checkout's unit suite — a family-repo name or a path",
    }
)
def unit(context, only=None, scope=None, repo=None):
    """Run every applicable unit-test runner (toolchain-aware)."""
    args: list[str] = []
    if only:
        args += ["--only", only]
    if scope:
        args += ["--scope", scope]
    if with_target(repo, _UNIT, args):
        return
    context.run(f"python -m modules.toolkit.{_UNIT} {' '.join(args)}".rstrip())


namespace = Collection("tests")
namespace.add_task(style)
namespace.add_task(unit)
