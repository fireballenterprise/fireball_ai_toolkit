"""``ai-toolkit`` console entrypoint.

Thin argparse shell over the primitives so the toolkit works with **no dependency added** via
``uvx --from git+https://github.com/fireballenterprise/fireball_ai_toolkit ai-toolkit <cmd>`` (e.g. the day-job repo).
The ``invoke ai_toolkit.*`` tasks in :mod:`fireball_ai_toolkit.tasks` are the in-repo equivalents.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import contribute as _contribute
from . import sync as _sync
from .apply import apply as _apply
from .check import check as _check

_ALIASES = {"download": "apply", "upload": "contribute"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-toolkit", description="Shared AI-agent tooling sync.")
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Consuming repo root (default: cwd)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="check .fireball_ai_toolkit/toolkit/ -> stop on local edits -> apply")
    p_sync.add_argument(
        "--yes", action="store_true", help="non-interactive: discard .fireball_ai_toolkit/toolkit/ edits"
    )

    sub.add_parser("apply", help="clobber .fireball_ai_toolkit/toolkit/ etc. from the installed package, then render")
    sub.add_parser(
        "contribute", help="open a PR against fireball_ai_toolkit with local .fireball_ai_toolkit/toolkit/ changes"
    )
    sub.add_parser("check", help="read-only drift gate")
    sub.add_parser("download", help="deprecated alias for `apply`")
    sub.add_parser("upload", help="deprecated alias for `contribute`")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo: Path = args.repo.resolve()
    command = _ALIASES.get(args.command, args.command)
    if command != args.command:
        print(f"note: `{args.command}` is now `{command}`", file=sys.stderr)

    if command == "apply":
        result = _apply(repo)
        print(f"Rendered {result.by_count} files.")
    elif command == "contribute":
        print(_contribute.contribute(repo))
    elif command == "check":
        _check(repo)
    elif command == "sync":
        plan = _sync.inspect(repo)
        print(plan.message)
        if plan.dirty and not args.yes:
            return 2
        result = _sync.run(repo, force=True)
        print(f"Rendered {result.by_count} files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
