"""Route /screenshots arguments to screenshot modules."""

from __future__ import annotations

import shlex
import subprocess
import sys

from ..common.route_utils import build_env, find_repo_root

_SUBCOMMAND_MODULES = {
    "configure": "modules.toolkit.screenshots.configure",
    "view": "modules.toolkit.screenshots.view",
    "clean": "modules.toolkit.screenshots.clean",
}


def _run(module: str, args: list[str]) -> int:
    repo_root = find_repo_root()
    env = build_env(repo_root)
    cmd = [sys.executable, "-m", module, *args]
    return subprocess.run(cmd, cwd=repo_root, env=env, check=False).returncode


def main() -> int:
    raw_args = sys.argv[1] if len(sys.argv) > 1 else ""
    args = shlex.split(raw_args)

    if not args:
        sys.stderr.write("Missing screenshots subcommand (configure | view | clean)\n")
        return 1

    first = args[0]
    module = _SUBCOMMAND_MODULES.get(first)
    if module is None:
        sys.stderr.write(f"Unknown screenshots subcommand: {first}\n")
        return 1

    return _run(module, args[1:])


if __name__ == "__main__":
    raise SystemExit(main())
