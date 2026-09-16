"""Shared plumbing for the per-tool lint / test runner modules."""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

#: A tool that ran clean.
OK = "ok"
#: A tool that reported real offences / failures — this fails ``invoke test``.
OFFENSES = "offenses"
#: A tool that didn't run (not applicable, or not installed) — never fails ``invoke test``.
SKIPPED = "skipped"


@dataclass
class ToolResult:
    """Outcome of one linter / test runner."""

    name: str
    status: str
    note: str = ""

    @property
    def failed(self) -> bool:
        return self.status == OFFENSES


def run(name: str, cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> ToolResult:
    """Run ``cmd`` in ``cwd``. A missing executable → ``SKIPPED`` (not a failure)."""
    exe = cmd[0]
    if shutil.which(exe) is None and not (cwd / exe).exists() and not Path(exe).is_absolute():
        return ToolResult(name, SKIPPED, f"{exe} not on PATH")
    proc = subprocess.run(cmd, cwd=cwd, env={**os.environ, **(env or {})}, check=False)
    if proc.returncode == 0:
        return ToolResult(name, OK)
    return ToolResult(name, OFFENSES, f"exit {proc.returncode}")


def gradlew(root: Path, tasks: list[str], *, name: str, env: dict[str, str] | None = None) -> ToolResult:
    """Run ``./gradlew <tasks>`` in ``root``. No wrapper → ``SKIPPED``.

    Calls the wrapper directly — never generates or commits it (that's the target repo's own
    setup task).
    """
    if not (root / "gradlew").exists():
        return ToolResult(name, SKIPPED, "no ./gradlew wrapper")
    cmd = ["./gradlew", *tasks, "--no-daemon", "--console=plain"]
    proc = subprocess.run(cmd, cwd=root, env={**os.environ, **(env or {})}, check=False)
    if proc.returncode == 0:
        return ToolResult(name, OK)
    return ToolResult(name, OFFENSES, f"exit {proc.returncode}")


def summarise(results: list[ToolResult]) -> int:
    """Print a one-line-per-tool summary; return 1 if any tool reported offences, else 0."""
    if not results:
        print("  (nothing applied to this repo)")
        return 0
    mark = {OK: "✓", OFFENSES: "✗", SKIPPED: "·"}
    width = max(len(result.name) for result in results)
    print("\n─── summary ───")
    for result in results:
        suffix = f"  {result.note}" if result.note else ""
        print(f"  {mark.get(result.status, ' ')} {result.name.ljust(width)}  {result.status}{suffix}")
    failed = [result.name for result in results if result.failed]
    if failed:
        print(f"\n{len(failed)} failed: {', '.join(failed)}")
        return 1
    return 0
