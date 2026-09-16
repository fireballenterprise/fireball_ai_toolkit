"""Invoke tasks shipped *inside the wheel* so a consuming repo mounts them in one line::

    from fireball_ai_toolkit.tasks import collection as toolkit_tasks
    namespace.add_collection(toolkit_tasks, name="toolkit")

Every task operates on the repo it is run from (``Path.cwd()``). Logic lives in the sibling
modules; these wrappers stay thin.

Verbs (apt-style):
  update      pull the newest toolkit release into the venv (uv lock --upgrade + uv sync)
  apply       clobber .fireball_ai_toolkit/toolkit/ + modules/toolkit/ + … from the installed package, then render
  upgrade     update, then apply — the whole "take the new toolkit" in one
  sync        apply, but stop first if .fireball_ai_toolkit/toolkit/ has local hand-edits
  contribute  open a PR to the toolkit with this repo's .fireball_ai_toolkit/toolkit/ edits
  check       read-only drift gate (wired into `invoke test`)
  release     dispatch the toolkit's own development -> main release
  mdfix       normalise markdown house style
"""

from __future__ import annotations

from pathlib import Path

from invoke import Collection, task

from . import contribute as _contribute
from . import sync as _sync
from .apply import apply as _apply
from .check import check as _check
from .mdfix import check_tree as _md_check
from .mdfix import fix_tree as _md_fix
from .release import release as _release

_PACKAGE = "fireball-ai-toolkit"


@task
def update(context):
    """Pull the newest toolkit release into the venv (uv lock --upgrade + uv sync).

    Nothing in the repo tree changes yet — follow with `apply` (or run `upgrade`).
    """
    context.run(f"uv lock --upgrade-package {_PACKAGE}")
    context.run("uv sync")


@task
def apply(context):  # noqa: ARG001
    """Clobber .fireball_ai_toolkit/toolkit/ + modules/toolkit/ + … from the installed package, then render."""
    result = _apply(Path.cwd())
    print(f"Rendered {result.by_count} files.")


@task
def upgrade(context, force=False):
    """update, then apply — pull the newest toolkit and take it into this repo.

    Stops if .fireball_ai_toolkit/toolkit/ has local hand-edits (pass --force to clobber them).
    """
    update(context)
    # The render MUST run in a fresh interpreter. `update` just swapped the package on disk, but
    # this process imported `_sync` (and its renderers/catalog) at startup and Python caches
    # imports — calling `_sync.run()` here would re-render with the *old* code (live bug: a
    # multi-version jump rendered stale `.sidecar/skills/*.md` stubs). Shelling out to the console
    # script picks up the just-installed version. Same `sync` semantics: stop on local .fireball_ai_toolkit/toolkit/
    # edits unless --force.
    result = context.run(
        f"uv run --no-sync ai-toolkit sync{' --yes' if force else ''}",
        warn=True,
        pty=False,
    )
    if result.exited == 2:
        raise SystemExit(2)  # .fireball_ai_toolkit/toolkit/ has local edits — re-run with --force to clobber them
    if result.exited != 0:
        raise SystemExit(result.exited)


@task
def sync(context, force=False):  # noqa: ARG001
    """Inspect .fireball_ai_toolkit/toolkit/ for local edits; if clean (or --force), apply (clobber + render)."""
    plan = _sync.inspect(Path.cwd())
    print(plan.message)
    if plan.dirty and not force:
        raise SystemExit(2)
    result = _sync.run(Path.cwd(), force=True)
    print(f"Rendered {result.by_count} files.")


@task
def contribute(context, branch=None, toolkit_repo=None):  # noqa: ARG001
    """Open a PR against fireball_ai_toolkit with this repo's .fireball_ai_toolkit/toolkit/ edits.

    The toolkit checkout is found via --toolkit-repo, then $FIREBALL_AI_TOOLKIT_REPO,
    then a sibling ../fireball_ai_toolkit dir.
    """
    kwargs = {"branch": branch}
    if toolkit_repo:
        kwargs["toolkit_repo"] = Path(toolkit_repo)
    print(_contribute.contribute(Path.cwd(), **kwargs))


@task
def check(context):  # noqa: ARG001
    """Read-only drift gate — fail if any generated provider file (or .fireball_ai_toolkit/toolkit/) is stale."""
    _check(Path.cwd())
    print("No drift.")


@task(help={"check": "read-only gate (raise instead of write)", "exclude": "comma-separated path segments to skip"})
def mdfix(context, check=False, exclude=""):  # noqa: ARG001
    """Normalise every *.md (no blank line after a header; no stray --- divider in instructions).

    Pass --check for the read-only gate (raises instead of writing) — wired into `invoke test`.
    --exclude=topics,vendor skips those trees (e.g. a separately-generated docs tree).
    """
    skip = tuple(part.strip() for part in exclude.split(",") if part.strip())
    if check:
        _md_check(Path.cwd(), exclude=skip)
        print("Markdown OK.")
        return
    changed = _md_fix(Path.cwd(), write=True, exclude=skip)
    print(f"Normalised {len(changed)} markdown file(s).")


@task
def release(context):  # noqa: ARG001
    """Dispatch the toolkit's development -> main release workflow."""
    print(_release(Path.cwd()))


@task
def download(context):
    """Deprecated alias for `apply`."""
    print("note: `ai_toolkit.download` is now `ai_toolkit.apply`")
    apply(context)


@task
def upload(context, branch=None, toolkit_repo=None):
    """Deprecated alias for `contribute`."""
    print("note: `ai_toolkit.upload` is now `ai_toolkit.contribute`")
    contribute(context, branch=branch, toolkit_repo=toolkit_repo)


collection = Collection("toolkit")
for _task in (update, apply, upgrade, sync, contribute, check, mdfix, release, download, upload):
    collection.add_task(_task)
