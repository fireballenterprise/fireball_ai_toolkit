"""Route `/backlog <subcommand> ...` to the matching backlog module (dispatch only)."""

from __future__ import annotations

import shlex
import subprocess
import sys

from ..common.route_utils import build_env, find_repo_root

_PREFIX = "modules.toolkit.backlog"
_SUBCOMMANDS = ("add", "close", "comment", "list", "start", "view")


def main() -> int:
    args = shlex.split(sys.argv[1] if len(sys.argv) > 1 else "")
    # Bare `/backlog` (the skill firing with no subcommand appended) → the whole-family open
    # backlog, matching the "backlog" / "what's open anywhere" trigger words. A real typo
    # (`args[0]` present but unknown) still gets the usage error.
    if not args:
        args = ["list", "--all"]
    elif args[0] not in _SUBCOMMANDS:
        sys.stderr.write(f"usage: backlog {{{'|'.join(_SUBCOMMANDS)}}} [options]\n")
        return 1

    subcommand, rest = args[0], args[1:]
    # `/backlog add bug --repo ...` → `--type bug`; the canonical flag form also works.
    if subcommand == "add" and rest and rest[0] in ("bug", "feature", "task"):
        rest = ["--type", rest[0], *rest[1:]]

    repo_root = find_repo_root()
    command = [sys.executable, "-m", f"{_PREFIX}.{subcommand}", *rest]
    return subprocess.run(command, cwd=repo_root, env=build_env(repo_root), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
