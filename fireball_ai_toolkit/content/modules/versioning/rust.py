"""Check the repo's pinned Rust toolchain (`rust-toolchain.toml`) against the latest stable, and — on apply —
rewrite the pin; also the repo-local install used by ``/upgrade``.

The family convention (Owner 2026-11-06): ONE repo (the orchestrator) owns the Rust toolchain, like the Python
venv or the ``.sdkmanrc`` JDK. It pins an exact version in ``rust-toolchain.toml`` and installs it into a
repo-local, gitignored ``.rust/`` (``RUSTUP_HOME=.rust/rustup``, ``CARGO_HOME=.rust/cargo``). Nothing touches
``~/.rustup`` or ``~/.cargo``. ``/update`` moves the pin; ``/upgrade`` installs what the pin says.

No ``rust-toolchain.toml`` (or a non-numeric channel such as ``stable``) → exits 3 ("nothing to do"), the same
convention ``libs`` / ``python`` / ``sdkman`` use, so ``versioning.check``'s loop can call it unconditionally.

Latest stable comes from the Rust channel manifest (``static.rust-lang.org/dist/channel-rust-stable.toml``,
stdlib ``urllib`` only). A release younger than ``MIN_AGE_DAYS`` is not adopted yet. Offline / unreachable →
a warning and exit 3, never a failure (CI-safe).
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import tomllib
import urllib.error
import urllib.request
from datetime import UTC, date, datetime
from pathlib import Path

from ..common import cli
from ..common.toolchains import owns_rust
from ..common.utils import info, success, version_tuple, warning
from ..setup.properties import get_repo_local

TOOLCHAIN_FILE = "rust-toolchain.toml"
MANIFEST_URL = "https://static.rust-lang.org/dist/channel-rust-stable.toml"
RUSTUP_INIT_URL = "https://static.rust-lang.org/rustup/dist/{triple}/rustup-init{exe}"
MIN_AGE_DAYS = 14
COMPONENTS = ("clippy", "rustfmt")
EXE = ".exe" if sys.platform == "win32" else ""

_CHANNEL_LINE = re.compile(r'^(\s*channel\s*=\s*")([^"]*)(".*)$', re.MULTILINE)


def toolchain_path(repo_path: Path) -> Path:
    return repo_path / TOOLCHAIN_FILE


def read_pin(repo_path: Path) -> str | None:
    """The exact version pinned in ``rust-toolchain.toml``; ``None`` when absent, unreadable or not a version."""
    try:
        channel = tomllib.loads(toolchain_path(repo_path).read_text(encoding="utf-8"))["toolchain"]["channel"]
    except OSError, ValueError, KeyError, TypeError:
        return None
    channel = str(channel)
    return channel if re.fullmatch(r"\d+\.\d+\.\d+", channel) else None


def read_components(repo_path: Path) -> list[str]:
    """``components`` of the pin file (default clippy + rustfmt)."""
    try:
        data = tomllib.loads(toolchain_path(repo_path).read_text(encoding="utf-8"))
        return [str(c) for c in data["toolchain"].get("components", COMPONENTS)]
    except OSError, ValueError, KeyError, TypeError:
        return list(COMPONENTS)


def write_pin(repo_path: Path, version: str) -> None:
    """Rewrite ``channel = "…"`` in place, keeping comments and the other keys."""
    path = toolchain_path(repo_path)
    text = path.read_text(encoding="utf-8")
    path.write_text(_CHANNEL_LINE.sub(lambda m: f"{m.group(1)}{version}{m.group(3)}", text, count=1), encoding="utf-8")


def fetch_manifest() -> dict | None:
    """The parsed stable channel manifest; ``None`` on any network/parse failure."""
    try:
        with urllib.request.urlopen(MANIFEST_URL, timeout=30) as response:  # noqa: S310 (fixed https URL)
            return tomllib.loads(response.read().decode("utf-8"))
    except urllib.error.URLError, OSError, ValueError, TimeoutError:
        return None


def latest_stable(manifest: dict) -> tuple[str, date] | None:
    """``(version, release_date)`` of the manifest's rustc, e.g. ``("1.99.1", date(2026, 10, 15))``."""
    try:
        version = re.match(r"(\d+\.\d+\.\d+)", manifest["pkg"]["rust"]["version"]).group(1)  # type: ignore[union-attr]
        released = date.fromisoformat(str(manifest["date"]))
    except KeyError, TypeError, AttributeError, ValueError:
        return None
    return version, released


def decide(current: str, latest: str, released: date, today: date | None = None) -> str | None:
    """The version to move to, or ``None`` (already current, newer-than-latest, or still too young)."""
    if version_tuple(latest) <= version_tuple(current):
        return None
    age = ((today or datetime.now(UTC).date()) - released).days
    return latest if age >= MIN_AGE_DAYS else None


# --- repo-local install (used by /upgrade; mirrors setup.local.sh `ensure_rust`) ---


def rust_dirs(repo_path: Path) -> tuple[Path, Path]:
    """``(RUSTUP_HOME, CARGO_HOME)`` inside the repo."""
    return repo_path / ".rust" / "rustup", repo_path / ".rust" / "cargo"


def local_env(repo_path: Path, *, toolchain: str | None = None) -> dict[str, str]:
    rustup_home, cargo_home = rust_dirs(repo_path)
    env = dict(os.environ)
    env["RUSTUP_HOME"] = str(rustup_home)
    env["CARGO_HOME"] = str(cargo_home)
    env["PATH"] = os.pathsep.join([str(cargo_home / "bin"), env.get("PATH", "")])
    env.pop("RUSTUP_TOOLCHAIN", None)
    if toolchain:
        env["RUSTUP_TOOLCHAIN"] = toolchain
    return env


def host_triple() -> str:
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    if sys.platform == "darwin":
        return "aarch64-apple-darwin" if arm else "x86_64-apple-darwin"
    if sys.platform == "win32":
        return "aarch64-pc-windows-msvc" if arm else "x86_64-pc-windows-msvc"
    return "aarch64-unknown-linux-gnu" if arm else "x86_64-unknown-linux-gnu"


def installed_toolchains(repo_path: Path) -> list[str]:
    """Toolchain directory names under ``.rust/rustup/toolchains`` (``1.99.1-aarch64-apple-darwin``)."""
    folder = rust_dirs(repo_path)[0] / "toolchains"
    return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else []


def is_installed(repo_path: Path, version: str) -> bool:
    """The repo-local rustup exists and the exact ``version`` toolchain is installed."""
    rustup = rust_dirs(repo_path)[1] / "bin" / f"rustup{EXE}"
    return rustup.is_file() and any(t.startswith(f"{version}-") for t in installed_toolchains(repo_path))


def superseded(repo_path: Path, version: str) -> list[str]:
    """Installed toolchains (rustup names) that are not the pinned ``version``."""
    return [t for t in installed_toolchains(repo_path) if not t.startswith(f"{version}-")]


def bootstrap_rustup(repo_path: Path) -> bool:
    """Download rustup-init and install rustup (no toolchain) into ``.rust/``. No profile edits, no sudo."""
    rustup_home, cargo_home = rust_dirs(repo_path)
    rustup_home.mkdir(parents=True, exist_ok=True)
    cargo_home.mkdir(parents=True, exist_ok=True)
    url = RUSTUP_INIT_URL.format(triple=host_triple(), exe=EXE)
    with tempfile.TemporaryDirectory() as tmp:
        init = Path(tmp) / f"rustup-init{EXE}"
        try:
            with urllib.request.urlopen(url, timeout=120) as response, init.open("wb") as handle:  # noqa: S310
                shutil.copyfileobj(response, handle)
        except urllib.error.URLError, OSError, TimeoutError:
            warning(f"Could not download rustup-init from {url}")
            return False
        init.chmod(init.stat().st_mode | stat.S_IXUSR)
        result = subprocess.run(
            [str(init), "-y", "--no-modify-path", "--default-toolchain", "none"],
            env=local_env(repo_path),
            check=False,
        )
    return result.returncode == 0


def install_pinned(repo_path: Path, version: str) -> bool:
    """Install exactly ``version`` repo-locally (bootstrapping rustup if needed), make it the default, and
    uninstall every superseded toolchain. Idempotent."""
    rustup = rust_dirs(repo_path)[1] / "bin" / f"rustup{EXE}"
    if not rustup.is_file() and not bootstrap_rustup(repo_path):
        return False
    env = local_env(repo_path)
    steps = [
        [str(rustup), "set", "auto-self-update", "disable"],
        [
            str(rustup),
            "toolchain",
            "install",
            version,
            "--profile",
            "minimal",
            *[arg for c in read_components(repo_path) for arg in ("-c", c)],
            "--no-self-update",
        ],
        [str(rustup), "default", version],
    ]
    for step in steps:
        if subprocess.run(step, env=env, cwd=repo_path, check=False).returncode != 0:
            warning(f"`{' '.join(step[1:])}` failed")
            return False
    for old in superseded(repo_path, version):
        info(f"Removing superseded Rust toolchain {old}")
        subprocess.run([str(rustup), "toolchain", "uninstall", old], env=env, cwd=repo_path, check=False)
    return True


@cli.command()
@cli.option("--dry-run", is_flag=True, help="Show updates without applying")
@cli.option("--yes", "-y", "no_confirm", is_flag=True, help="Skip confirmation")
def main(dry_run: bool, no_confirm: bool) -> None:
    """Check the ``rust-toolchain.toml`` pin against the latest stable Rust and rewrite it when newer.

    This updates the pin only. Installing it (``.rust/``) is the ``/upgrade`` step. No exact-version
    ``rust-toolchain.toml`` in this repo → nothing to do.
    """
    info("Checking rust-toolchain.toml...")
    repo_path = get_repo_local()
    current = read_pin(repo_path)
    if not owns_rust(repo_path):
        success("This repo does not own the Rust toolchain (the orchestrator does) — nothing to check")
        raise SystemExit(3)
    if current is None:
        success("No exact-version rust-toolchain.toml in this repo — nothing to check")
        raise SystemExit(3)

    manifest = fetch_manifest()
    latest = latest_stable(manifest) if manifest else None
    cli.echo("\n📊 Rust Toolchain Status:")
    if latest is None:
        warning("Could not read the Rust channel manifest (offline?) — skipping the Rust check")
        cli.echo(f"   rust       {current}  (not checked)")
        raise SystemExit(3)

    version, released = latest
    target = decide(current, version, released)
    if target is None:
        if version_tuple(version) > version_tuple(current):
            cli.echo(f"   rust       {current}  ({version} released {released}, waiting {MIN_AGE_DAYS} days)")
        else:
            cli.echo(f"   rust       {current}  (current)")
        cli.echo()
        success("Rust pin is current")
        raise SystemExit(3)

    cli.echo(f"   rust       {current}  →  {target}  (released {released})")
    if dry_run:
        cli.echo("\n🔍 Dry-run mode: No changes made")
        return
    if not no_confirm and not cli.confirm(f"💡 Update {TOOLCHAIN_FILE} to {target}?"):
        cli.echo("Cancelled.")
        raise SystemExit(2)

    write_pin(repo_path, target)
    cli.echo(f"\n✏️  Updated {TOOLCHAIN_FILE}")
    cli.echo("\n💡 Run /upgrade to install the new toolchain (into .rust/)")
    cli.echo()


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
