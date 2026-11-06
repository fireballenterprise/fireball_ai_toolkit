"""Shared plumbing for the per-tool lint / test runner modules."""

from __future__ import annotations

import os
import re
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


def pinned_rust_env(start: Path | None = None) -> dict[str, str]:
    """The environment that makes ``cargo`` the orchestrator's repo-local, pinned toolchain (``.rust/`` + ``rust-toolchain.toml``).

    Found by walking up from this module to the checkout that owns the pin (a directory holding ``rust-toolchain.toml`` and
    ``.rust/cargo/bin``). Empty when there is none (a repo that does not own Rust, or Rust not installed yet), so plain ``cargo``
    on PATH is used as before. Mirrors the orchestrator's ``modules/rust/toolchain.py`` ``rust_env()`` without importing it (this
    module is copied into every consuming repo)."""
    for parent in (start or Path(__file__)).resolve().parents:
        pin = parent / "rust-toolchain.toml"
        cargo_bin = parent / ".rust" / "cargo" / "bin"
        if pin.is_file() and cargo_bin.is_dir():
            match = re.search(r'^\s*channel\s*=\s*"([^"]+)"', pin.read_text(encoding="utf-8"), re.MULTILINE)
            env = {
                "RUSTUP_HOME": str(parent / ".rust" / "rustup"),
                "CARGO_HOME": str(parent / ".rust" / "cargo"),
                "PATH": f"{cargo_bin}{os.pathsep}{os.environ.get('PATH', '')}",
            }
            if match:
                env["RUSTUP_TOOLCHAIN"] = match.group(
                    1
                )  # so a product repo's own toolchain file cannot trigger a second install
            return env
    return {}


def run(name: str, cmd: list[str], cwd: Path, *, env: dict[str, str] | None = None) -> ToolResult:
    """Run ``cmd`` in ``cwd``. A missing executable → ``SKIPPED`` (not a failure), except ``cargo``: a Rust repo with no toolchain
    is a failure, never a silent skip. ``cargo`` runs with the orchestrator's pinned, repo-local toolchain when it has one."""
    exe = cmd[0]
    merged = {**os.environ, **(env or {})}
    if exe == "cargo":
        merged.update(pinned_rust_env())
    if shutil.which(exe, path=merged.get("PATH")) is None and not (cwd / exe).exists() and not Path(exe).is_absolute():
        if exe == "cargo":
            return ToolResult(
                name, OFFENSES, "cargo not found: run `invoke setup` (the orchestrator owns the Rust toolchain)"
            )
        return ToolResult(name, SKIPPED, f"{exe} not on PATH")
    proc = subprocess.run(cmd, cwd=cwd, env=merged, check=False)
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
