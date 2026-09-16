"""Shared ``--repo`` handling for the flat toolkit task wrappers.

``with_target(repo, module_suffix, args)`` resolves the selector; when it names another checkout
it delegates the module there as a fresh subprocess and returns ``True`` (the caller returns
immediately, propagating a non-zero exit via ``SystemExit``). ``repo=None`` → returns ``False``
and the caller runs its normal ``context.run(...)``.
"""

from __future__ import annotations

from pathlib import Path


def with_target(repo: str | None, module_suffix: str, args: list[str]) -> bool:
    """See module docstring. ``module_suffix`` is relative to the toolkit package,
    e.g. ``"versioning.check"`` or ``"tests.style"``."""
    if not repo:
        return False
    from modules.toolkit.common.target_repo import delegate, resolve_target_repo  # noqa: PLC0415

    target = resolve_target_repo(repo)  # SystemExit + candidate list on an ambiguous name
    if target is None:
        return False
    code = delegate(target, module_suffix, args, caller_root=Path.cwd())
    if code != 0:
        raise SystemExit(code)
    return True
