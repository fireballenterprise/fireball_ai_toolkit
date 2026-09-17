"""Route /topic arguments to topic modules."""

from __future__ import annotations

import logging
import shlex
import subprocess
import sys

from ..common.route_utils import build_env, find_repo_root

LOGGER = logging.getLogger(__name__)

_SUBCOMMANDS = {"init", "list", "new", "reindex", "switch", "update"}

# `modules.toolkit.topic` when vendored, `modules.topic` flat — resolve against our own package so
# the file is identical either way.
_PKG = __package__ or "modules.topic"
_SUBCOMMAND_MODULES = {name: f"{_PKG}.{name}" for name in _SUBCOMMANDS}


def _run(module: str, args: list[str]) -> int:
    repo_root = find_repo_root()
    env = build_env(repo_root)
    cmd = [sys.executable, "-m", module, *args]
    completed = subprocess.run(cmd, cwd=repo_root, env=env, check=False)
    return completed.returncode


def _switch_args(args: list[str]) -> list[str]:
    if not args:
        sys.stderr.write("Missing topic path\n")
        raise SystemExit(1)
    return [f"--path={args[0]}"]


def _split_positional_and_flags(args: list[str]) -> tuple[list[str], list[str]]:
    positional = [a for a in args if not a.startswith("-")]
    flags = [a for a in args if a.startswith("-")]
    return positional, flags


def _new_args(args: list[str]) -> list[str]:
    if not args:
        sys.stderr.write("Missing topic path\n")
        raise SystemExit(1)
    positional, passthrough = _split_positional_and_flags(args)
    flags = [f"--path={positional[0]}"]
    if len(positional) > 1:
        flags.append(f"--description={' '.join(positional[1:])}")
    return flags + passthrough


def _init_args(args: list[str]) -> list[str]:
    positional, passthrough = _split_positional_and_flags(args)
    flags = [f"--description={' '.join(positional)}"] if positional else []
    return flags + passthrough


def _list_args(args: list[str]) -> list[str]:
    return ["--all"] if args and args[0] == "all" else []


_ARG_BUILDERS = {
    "init": _init_args,
    "list": _list_args,
    "new": _new_args,
    "switch": _switch_args,
}


def main() -> int:
    raw_args = sys.argv[1] if len(sys.argv) > 1 else ""
    args = shlex.split(raw_args)

    if not args:
        sys.stderr.write("Missing topic subcommand or path\n")
        return 1

    first = args[0]
    if first in _SUBCOMMANDS:
        subcommand, rest = first, args[1:]
    else:
        subcommand, rest = "switch", args

    flags = rest if subcommand in ("update", "reindex") else _ARG_BUILDERS[subcommand](rest)

    return _run(_SUBCOMMAND_MODULES[subcommand], flags)


if __name__ == "__main__":
    raise SystemExit(main())
