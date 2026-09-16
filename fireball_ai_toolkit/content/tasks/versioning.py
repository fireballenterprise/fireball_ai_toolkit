"""Thin wrappers over ``modules.toolkit.versioning`` — ``check`` / ``upgrade`` / ``bump``.

All logic is in the module; these only translate invoke kwargs to CLI flags and route ``--repo``
to another checkout. Registered by consumers as both ``versioning.*`` and the short alias
``ver.*``, plus top-level ``update`` (= ``versioning.check``) and ``upgrade`` (= ``versioning.upgrade``).

The sub-arg is ``--only`` here (invoke can't have an *optional* positional); the slash commands
(``/update libs``) take it as a bare positional via ``versioning/route.py``.
"""

from invoke import Collection, task

from ._targets import with_target

_CHECK = "versioning.check"
_UPGRADE = "versioning.upgrade"
_BUMP = "versioning.project"


def _flags(dry_run: bool, yes: bool) -> list[str]:
    out: list[str] = []
    if dry_run:
        out.append("--dry-run")
    if yes:
        out.append("--yes")
    return out


@task(
    help={
        "only": "Force one sub-check: libs | python | workflows | sdkman (default: every applicable one)",
        "repo": "Run against another checkout — a family-repo name or a path",
        "dry-run": "Preview only, never write",
        "yes": "Skip confirmation prompts",
    }
)
def check(context, only=None, repo=None, dry_run=False, yes=False):
    """Run the applicable version checks (toolchain-aware). Was ``ver.libs`` / ``ver.update``."""
    args = (["--only", only] if only else []) + _flags(dry_run, yes)
    if with_target(repo, _CHECK, args):
        return
    context.run("python -m modules.toolkit.setup.properties")
    result = context.run(f"python -m modules.toolkit.{_CHECK} {' '.join(args)}".rstrip(), warn=True)
    if result.exited != 0:
        raise SystemExit(result.exited)


@task(
    help={
        "only": "Force one: uv | python | libs | sdkman (default: every applicable one)",
        "sync": "Just `uv sync --upgrade` — no version checks",
        "repo": "Run against another checkout — a family-repo name or a path",
        "yes": "Skip confirmation prompts",
    }
)
def upgrade(context, only=None, sync=False, repo=None, yes=False):
    """Install the upgrades reviewed by ``check`` — uv + Python binaries, .venv, libs, SDKMAN."""
    args: list[str] = []
    if only:
        args += ["--only", only]
    if sync:
        args.append("--sync")
    if yes:
        args.append("--yes")
    if with_target(repo, _UPGRADE, args):
        return
    context.run(f"python -m modules.toolkit.{_UPGRADE} {' '.join(args)}".rstrip())


@task(help={"part": "patch | minor | major | build", "repo": "Run against another checkout (path only)"})
def bump(context, part, repo=None):
    """Bump the root VERSION file. Was ``ver.project_bump_patch`` etc."""
    if with_target(repo, _BUMP, [part]):
        return
    context.run(f"python -m modules.toolkit.{_BUMP} {part}")


namespace = Collection("versioning")
namespace.add_task(check)
namespace.add_task(upgrade)
namespace.add_task(bump)
