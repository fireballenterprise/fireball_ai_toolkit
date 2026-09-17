"""Route /chat arguments to chat modules."""

from __future__ import annotations

import logging
import shlex
import subprocess
import sys

from ..common.route_utils import build_env, find_repo_root

LOGGER = logging.getLogger(__name__)

_SUBCOMMANDS = {"end", "list", "resume", "start"}

# `modules.toolkit.chat` when vendored, `modules.chat` flat — resolve against our own package so
# the file is identical either way.
_PKG = __package__ or "modules.chat"
_SUBCOMMAND_MODULES = {name: f"{_PKG}.{name}" for name in _SUBCOMMANDS}


def _run(module: str, args: list[str]) -> int:
    repo_root = find_repo_root()
    env = build_env(repo_root)
    cmd = [sys.executable, "-m", module, *args]
    completed = subprocess.run(cmd, cwd=repo_root, env=env, check=False)
    return completed.returncode


def _start_args(args: list[str]) -> list[str]:
    return [f"--title={' '.join(args)}"] if args else []


def _resume_args(args: list[str]) -> list[str]:
    return [f"--pattern={' '.join(args)}"] if args else []


_ARG_BUILDERS = {
    "resume": _resume_args,
    "start": _start_args,
}


def main() -> int:
    raw_args = sys.argv[1] if len(sys.argv) > 1 else ""
    args = shlex.split(raw_args)

    if not args:
        sys.stderr.write("Missing chat subcommand\n")
        return 1

    first = args[0]
    if first not in _SUBCOMMANDS:
        sys.stderr.write(f"Unknown chat subcommand: {first}\n")
        return 1

    rest = args[1:]
    builder = _ARG_BUILDERS.get(first)
    flags = builder(rest) if builder else []

    return _run(_SUBCOMMAND_MODULES[first], flags)


if __name__ == "__main__":
    raise SystemExit(main())
