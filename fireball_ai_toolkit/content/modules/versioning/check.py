"""Run every version check that applies to this repo — the orchestrator behind ``/update`` and
``invoke versioning.check``.

With no sub-check named it inspects the repo's toolchains (``common.toolchains``) and runs only
the checks that apply: a Python library gets ``libs`` + ``python``, a repo with workflows gets
``workflows``, a repo with a ``.sdkmanrc`` gets ``sdkman``. Name one (``libs`` / ``python`` /
``workflows`` / ``sdkman``) to force just that one even if its toolchain isn't detected.

Each sub-check runs as its own ``python -m modules.toolkit.versioning.<name>`` subprocess so one
exiting early (exit 3 = "nothing to do") never stops the others. Overall exit is non-zero only
when a sub-check genuinely failed.
"""

from __future__ import annotations

import subprocess

from ..common import cli
from ..common.route_utils import find_repo_root
from ..common.toolchains import capabilities
from ..common.utils import info, success

#: Sub-checks in run order, mapped to the capability string that turns each on.
_CHECKS: dict[str, str] = {
    "libs": "check:libs",
    "python": "check:python",
    "workflows": "check:workflows",
    "sdkman": "check:sdkman",
}

_OK_EXIT_CODES = (0, 3)


def _run_one(name: str, flags: list[str]) -> int:
    module = f"{__package__}.{name}"
    completed = subprocess.run(
        ["uv", "run", "--no-sync", "python", "-m", module, *flags],
        check=False,
    )
    return completed.returncode


@cli.command()
@cli.option("--only", help="Run just this sub-check (libs | python | workflows | sdkman)")
@cli.option("--dry-run", is_flag=True, help="Show updates without applying")
@cli.option("--yes", "-y", "no_confirm", is_flag=True, help="Skip confirmation prompts")
def main(only: str | None, dry_run: bool, no_confirm: bool) -> None:
    """Run the applicable version checks (or just ``--only <name>``)."""
    if only and only not in _CHECKS:
        cli.echo(f"Unknown check {only!r} — pick one of: {', '.join(_CHECKS)}", err=True)
        raise SystemExit(2)

    if only:
        selected = [only]
    else:
        caps = capabilities(find_repo_root())
        selected = [name for name, cap in _CHECKS.items() if cap in caps]
        skipped = [name for name in _CHECKS if name not in selected]
        if skipped:
            info(f"Skipping (toolchain not present): {', '.join(skipped)}")

    if not selected:
        success("No version checks apply to this repo.")
        return

    flags: list[str] = []
    if dry_run:
        flags.append("--dry-run")
    if no_confirm:
        flags.append("--yes")

    failures: list[str] = []
    for name in selected:
        cli.echo(f"\n═══ versioning.check {name} ═══")
        code = _run_one(name, flags)
        if code not in _OK_EXIT_CODES:
            failures.append(name)

    if failures:
        cli.echo(f"\n✗ failed: {', '.join(failures)}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
