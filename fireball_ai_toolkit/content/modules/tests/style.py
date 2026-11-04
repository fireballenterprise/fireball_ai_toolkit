"""``tests.style`` — run every linter / formatter that applies to this repo.

No ``--only`` → the toolchains present decide which run (Python repo: ruff + pylint + yamllint +
actionlint; Kotlin repo: ktlint + detekt + android-lint; Rust repo: rustfmt + clippy + cargo-deny; …). ``--fix`` applies autofixes where the
tool supports it. Exit is non-zero only when a tool reported real offences — a tool that isn't
installed is reported as skipped, never a failure.
"""

from __future__ import annotations

from ..common import cli
from ..common.route_utils import find_repo_root
from ..common.utils import info
from . import actionlint, android_lint, cargo_deny, clippy, detekt, ktlint, pylint, ruff, rustfmt, yamllint
from .common import summarise

#: display name → tool module, in run order.
_LINTERS = {
    "ruff": ruff,
    "pylint": pylint,
    "yamllint": yamllint,
    "actionlint": actionlint,
    "ktlint": ktlint,
    "detekt": detekt,
    "android-lint": android_lint,
    "rustfmt": rustfmt,
    "clippy": clippy,
    "cargo-deny": cargo_deny,
}


@cli.command()
@cli.option(
    "--only",
    help=(
        "Run just this linter (ruff | pylint | yamllint | actionlint | ktlint | detekt | android-lint"
        " | rustfmt | clippy | cargo-deny)"
    ),
)
@cli.option("--fix", is_flag=True, help="Apply autofixes where the tool supports it")
def main(only: str | None, fix: bool) -> None:
    root = find_repo_root()

    if only and only not in _LINTERS:
        cli.echo(f"Unknown linter {only!r} — pick one of: {', '.join(_LINTERS)}", err=True)
        raise SystemExit(2)

    if only:
        names = [only]
    else:
        names = [name for name, module in _LINTERS.items() if module.applies(root)]
        # `--fix` with no target = "apply autofixes" — run only the tools that can fix (ruff,
        # ktlint, rustfmt, clippy), not the check-only linters (that's `tests.style` / `invoke test`).
        if fix:
            names = [name for name in names if hasattr(_LINTERS[name], "fix")]
    if not names:
        cli.echo("Nothing to do." if fix else "No linters apply to this repo.")
        return
    if not only:
        skipped = [name for name in _LINTERS if name not in names]
        if skipped:
            info(f"Skipping ({'no autofix' if fix else 'toolchain not present'}): {', '.join(skipped)}")

    results = []
    for name in names:
        module = _LINTERS[name]
        cli.echo(f"\n─── {name}{' (fix)' if fix else ''} ───")
        if fix and hasattr(module, "fix"):
            results.append(module.fix(root))
        else:
            results.append(module.check(root))

    code = summarise(results)
    if code:
        raise SystemExit(code)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
