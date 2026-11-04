"""``tests.unit`` — run every unit-test runner that applies to this repo.

Python repo → pytest (``--scope`` passes a marker expression through); Kotlin/Gradle repo →
``./gradlew testDebugUnitTest``; Rust repo → ``cargo test --workspace --release``
(``--scope`` is the test-name filter).
"""

from __future__ import annotations

from ..common import cli
from ..common.route_utils import find_repo_root
from ..common.utils import info
from . import cargo_test, gradle_unit
from . import pytest as pytest_runner
from .common import summarise

_RUNNERS = {
    "pytest": pytest_runner,
    "gradle-unit": gradle_unit,
    "cargo-test": cargo_test,
}


@cli.command()
@cli.option("--only", help="Run just this runner (pytest | gradle-unit | cargo-test)")
@cli.option("--scope", help="pytest marker expression ('versioning', 'not style') or a cargo test-name filter")
def main(only: str | None, scope: str | None) -> None:
    root = find_repo_root()

    if only and only not in _RUNNERS:
        cli.echo(f"Unknown runner {only!r} — pick one of: {', '.join(_RUNNERS)}", err=True)
        raise SystemExit(2)

    names = [only] if only else [name for name, module in _RUNNERS.items() if module.applies(root)]
    if not names:
        cli.echo("No unit-test runners apply to this repo.")
        return
    if not only:
        skipped = [name for name in _RUNNERS if name not in names]
        if skipped:
            info(f"Skipping (toolchain not present): {', '.join(skipped)}")

    results = []
    for name in names:
        cli.echo(f"\n─── {name} ───")
        results.append(_RUNNERS[name].check(root, scope=scope))

    code = summarise(results)
    if code:
        raise SystemExit(code)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
