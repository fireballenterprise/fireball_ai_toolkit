"""Route ``/update`` and ``/upgrade`` to the ``versioning`` modules, peeling off the
``--repo`` / bare-repo target selector first.

Exec lines (from the command files)::

    /update   -> python -m modules.toolkit.versioning.route "check $ARGUMENTS"
    /upgrade  -> python -m modules.toolkit.versioning.route "upgrade $ARGUMENTS"

So the first token is the verb (``check`` | ``upgrade`` | ``bump``); the rest is a mix of an
optional target (``--repo <name|path>`` or a bare leading token), an optional sub-arg
(``libs`` / ``python`` / ``workflows`` / ``sdkman`` for check; ``python`` / ``libs`` / ``sdkman``
for upgrade; ``patch`` / ``minor`` / ``major`` / ``build`` for bump), and pass-through flags
(``--dry-run``, ``--yes``, ``--sync``).
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from pathlib import Path

from ..common.route_utils import peel_repo
from ..common.target_repo import delegate, resolve_target_repo

#: verb → (module suffix under the toolkit package, recognised sub-args)
_VERBS: dict[str, tuple[str, set[str]]] = {
    "check": ("versioning.check", {"libs", "python", "workflows", "sdkman"}),
    "upgrade": ("versioning.upgrade", {"uv", "python", "libs", "sdkman"}),
    "bump": ("versioning.project", {"patch", "minor", "major", "build"}),
}

_BASE = __package__.rsplit(".", 1)[0] if __package__ else "modules"


def _module_args(verb: str, only: str | None, passthrough: list[str]) -> list[str]:
    if verb == "bump":
        return ([only] if only else []) + passthrough
    return (["--only", only] if only else []) + passthrough


def main() -> int:
    raw = sys.argv[1:]
    args = shlex.split(raw[0]) if len(raw) == 1 else list(raw)

    if not args or args[0] in ("-h", "--help", "help"):
        sys.stdout.write(
            "usage: versioning.route <check|upgrade|bump> [<repo>] [<sub-arg>] "
            "[--repo <name|path>] [--dry-run] [--yes] [--sync]\n"
        )
        return 0 if args else 1

    verb, rest = args[0], args[1:]
    if verb not in _VERBS:
        sys.stderr.write(f"versioning.route: unknown verb {verb!r} (check | upgrade | bump)\n")
        return 1
    module_suffix, subargs = _VERBS[verb]

    rest, repo_token = peel_repo(rest)
    # Bare-repo shorthand: a leading positional that is neither a flag nor a known sub-arg.
    if repo_token is None and rest and not rest[0].startswith("-") and rest[0] not in subargs:
        repo_token = rest.pop(0)

    only: str | None = None
    passthrough: list[str] = []
    for token in rest:
        if only is None and token in subargs:
            only = token
        else:
            passthrough.append(token)

    module_args = _module_args(verb, only, passthrough)

    target = resolve_target_repo(repo_token)
    if target is not None:
        return delegate(target, module_suffix, module_args, caller_root=Path.cwd())

    completed = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-m", f"{_BASE}.{module_suffix}", *module_args],
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
