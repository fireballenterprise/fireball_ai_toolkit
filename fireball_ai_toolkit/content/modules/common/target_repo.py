"""Resolve a ``--repo`` / first-positional target selector to a checkout path, and delegate a
toolkit module into that checkout.

Every retargetable task and router calls :func:`resolve_target_repo` with whatever the user passed
(a fuzzy family-repo name, a filesystem path, or ``None``) and — when it returns a path —
:func:`delegate` to re-exec the real work as a fresh subprocess in that checkout. A fresh process
is mandatory: ``setup.properties`` caches the repo root / parsed ``properties.yml`` for the life of
the process (``@lru_cache``), so one process cannot cleanly act on two repos.

**CI-safe**: importing this module pulls in nothing but the stdlib + ``common.utils`` /
``common.route_utils`` (also stdlib-only). ``setup.properties`` / ``backlog.common`` are imported
lazily, only when a bare *name* has to be resolved — the path branch and the ``None`` branch never
touch ``properties.yml`` (git-ignored, absent in CI).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .route_utils import REPO_ROOT_ENV
from .utils import error

__all__ = ["REPO_ROOT_ENV", "delegate", "pkg_root", "resolve_target_repo"]


def _looks_like_path(token: str) -> bool:
    """A token is a filesystem path (not a family-repo name) when it holds a path separator or
    starts with ``.`` / ``~`` / the root ``/``."""
    if os.sep in token or (os.altsep and os.altsep in token):
        return True
    return token.startswith((".", "~", "/"))


def resolve_target_repo(token: str | None) -> Path | None:
    """Map a ``--repo`` selector to an absolute checkout path.

    - ``None`` / empty  → ``None`` (caller keeps its normal cwd / ``properties.yml`` behaviour;
      nothing is imported — the CI short-circuit).
    - a path-shaped token → ``Path(token).expanduser().resolve()``, verified to hold a ``.git``;
      ``properties.yml`` is never consulted.
    - a bare name → fuzzy-matched against the ``repos:`` family (via ``backlog.common.resolve_repo``).
      With no ``repos:`` map (a plain consumer repo, or CI) this ``error()``s and tells the caller
      to pass a path instead.
    """
    if not token or not token.strip():
        return None
    token = token.strip()

    if _looks_like_path(token):
        path = Path(token).expanduser().resolve()
        if not (path / ".git").exists():
            error(f"--repo {token!r}: {path} is not a git checkout (no .git)")
        return path

    # Bare name — needs properties.yml. Import lazily so the path / None branches stay CI-safe.
    from ..backlog.common import resolve_repo  # noqa: PLC0415
    from ..setup.properties import get_family_repos  # noqa: PLC0415

    try:
        family = get_family_repos(include_self=True, include_retired=True, include_missing=True)
    except FileNotFoundError:
        family = []
    if not family:
        error(
            f"--repo {token!r}: this repo has no properties.yml repos:/repos_local: map — "
            f"pass a filesystem path instead (e.g. --repo ../other_repo)"
        )

    repo = resolve_repo(token)  # SystemExit + candidate list on an ambiguous / unknown name
    if not repo.path or not (repo.path / ".git").exists():
        error(f"--repo {token!r}: resolved to {repo.path}, which has no local clone")
    return repo.path


def pkg_root(path: Path) -> str:
    """Importable prefix for a repo's vendored toolkit modules — ``modules.toolkit`` in a consumer
    that vendors the toolkit, plain ``modules`` in the template layout."""
    return "modules.toolkit" if (path / "modules" / "toolkit" / "repo").is_dir() else "modules"


def delegate(target: Path, module_suffix: str, args: list[str], *, caller_root: Path) -> int:
    """Re-exec ``python -m <pkg>.<module_suffix> <args>`` against ``target`` as a fresh subprocess.

    When ``target`` vendors the toolkit the module runs in the target's own checkout + venv
    (``cwd=target``). When it doesn't (no ``modules/toolkit/`` — e.g. a Kotlin app or a Shopify
    store) the **caller's** vendored module runs with ``cwd`` at the caller and
    ``$SIDECAR_REPO_ROOT`` pointed at the target so file-scanning checks still hit the right tree.
    """
    vendored = (target / "modules" / "toolkit").is_dir()
    cwd = target if vendored else caller_root
    module = f"{pkg_root(cwd)}.{module_suffix}"
    env = {**os.environ, REPO_ROOT_ENV: str(target)}
    completed = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-m", module, *args],
        cwd=cwd,
        env=env,
        check=False,
    )
    return completed.returncode
