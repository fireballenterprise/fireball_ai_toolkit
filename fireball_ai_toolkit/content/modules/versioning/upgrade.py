"""Execute Python and/or library upgrades."""

import logging
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

from ..common import cli
from ..common.toolchains import owns_rust
from ..common.utils import error, info, success, version_tuple, warning
from ..setup.properties import get_binary_version, get_repo_local

# Import check functions
from .libs import get_declared_dependency_names, get_outdated_packages, load_pyproject
from .python import get_runtime_python_version
from .rust import install_pinned, is_installed, read_pin
from .sdkman import _channel_suffix, latest_identifier, read_sdkmanrc, read_skip_list

LOGGER = logging.getLogger(__name__)


def rebuild_venv(repo_path: Path, python_version: str) -> None:
    """Install `python_version` via uv, then remove .venv and recreate it (via setup.sh) so the
    rebuilt venv lands on exactly that version rather than whatever setup.sh's own floating
    `--python` spec happens to resolve to."""
    info(f"Installing Python {python_version}...")
    result = subprocess.run(["uv", "python", "install", python_version], check=False)
    if result.returncode != 0:
        error(f"uv python install {python_version} failed")

    venv_path = repo_path / ".venv"

    if venv_path.exists():
        cli.echo("🗑️  Removing existing .venv...")
        shutil.rmtree(venv_path)

    cli.echo("🏗️  Running setup.sh to create new .venv...")
    result = subprocess.run(
        ["bash", "setup.sh"],
        cwd=repo_path,
        check=False,
    )

    if result.returncode != 0:
        warning("setup.sh completed with warnings")
    else:
        success("Virtual environment rebuilt successfully")


def run_uv_sync() -> None:
    """Run uv sync --upgrade to install updated dependencies."""
    info("Syncing dependencies with uv...")

    result = subprocess.run(
        ["uv", "sync", "--upgrade"],
        check=False,
    )

    if result.returncode != 0:
        error("uv sync --upgrade failed")

    success("Dependencies synced")


def upgrade_uv_binary() -> None:
    """Upgrade the ``uv`` binary itself — it's unpinned (always latest). Homebrew when present,
    otherwise ``uv self update`` (the standalone installer's own updater). Idempotent — a no-op
    when uv is already current."""
    if shutil.which("brew"):
        info("Upgrading uv via Homebrew...")
        cmd = ["brew", "upgrade", "uv"]
    else:
        info("Upgrading uv via `uv self update`...")
        cmd = ["uv", "self", "update"]
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        warning(f"`{' '.join(cmd)}` completed with warnings (uv may be pip-managed — upgrade it there)")
    else:
        success("uv is up to date")


def check_python_needs_upgrade(_repo_path: Path) -> tuple[bool, str, str]:
    """Check whether the active Python runtime matches properties.yml's pinned version — the
    exact version `/update python` last wrote there, and the one this upgrade installs (kept as
    the single source of truth, same as `binary_versions.cdk`/`aws.cdk.upgrade`).

    Returns:
        (needs_upgrade, current_runtime_version, pinned_version)
    """
    current_runtime = get_runtime_python_version()
    try:
        pinned_version = get_binary_version("python")
    except KeyError:
        return (False, current_runtime, current_runtime)  # no binary_versions.python pin — nothing to do
    needs_upgrade = version_tuple(current_runtime) < version_tuple(pinned_version)

    return (needs_upgrade, current_runtime, pinned_version)


def check_libs_need_upgrade(repo_path: Path) -> tuple[bool, int]:
    """Check if any declared dependency has an installed version older than what's available.

    Compares *installed* package versions against `uv pip list --outdated`, not pyproject.toml's
    specifier string against the latest version (that's `find_updates`, used by `ver.libs` to
    detect config drift) — `/update` may already have bumped the specifier before the matching
    `uv sync --upgrade` ever ran, which would make a specifier-vs-latest check report nothing to
    do even though `.venv`/`uv.lock` are still on the old version.

    Returns:
        (needs_upgrade, count_of_updates)
    """
    outdated_packages = get_outdated_packages()
    toml_doc, _ = load_pyproject(repo_path)
    declared = get_declared_dependency_names(toml_doc)

    relevant_outdated = [pkg for pkg in outdated_packages if pkg["name"].lower() in declared]
    return (len(relevant_outdated) > 0, len(relevant_outdated))


def _apple_silicon() -> bool:
    """True on an arm64 Mac (the native architecture SDKMAN must install for)."""
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _sdkman_dir() -> Path:
    return Path(os.environ.get("SDKMAN_DIR", Path.home() / ".sdkman"))


def ensure_native_sdkman_platform() -> bool:
    """On Apple Silicon make SDKMAN fetch arm64 builds: its default config ships
    `sdkman_rosetta2_compatible=true`, which makes `infer_platform` answer `darwinx64` even on an
    arm64 shell, so every JDK lands as an x86_64 binary that dies with "Bad CPU type in executable"
    when there is no Rosetta. Flips that flag to `false`. Returns True when the config was changed."""
    if not _apple_silicon():
        return False
    config = _sdkman_dir() / "etc" / "config"
    if not config.is_file():
        return False
    text = config.read_text(encoding="utf-8")
    updated = re.sub(r"^(sdkman_rosetta2_compatible\s*=\s*)true\s*$", r"\1false", text, flags=re.MULTILINE)
    if updated == text:
        return False
    config.write_text(updated, encoding="utf-8")
    warning("SDKMAN was set to Rosetta (x86_64) mode; switched sdkman_rosetta2_compatible to false for native arm64")
    return True


def _sdk_shell_command(script: str) -> list[str]:
    """argv running `script` in a login shell with sdkman-init.sh sourced — under `arch -arm64` on
    Apple Silicon, so the shell (and SDKMAN's platform detection) is native even if the caller is not."""
    argv = ["bash", "-lc", f'source "$HOME/.sdkman/bin/sdkman-init.sh" && {script}']
    return ["arch", "-arm64", *argv] if _apple_silicon() else argv


def _run_sdk_env_install(repo_path: Path) -> tuple[int, str]:
    """Run `sdk env install` in a login shell; echo its output and return `(exit code, output)`."""
    result = subprocess.run(
        _sdk_shell_command("sdk env install 2>&1"),
        cwd=repo_path,
        stdout=subprocess.PIPE,
        text=True,
        check=False,
    )
    output = result.stdout or ""
    if output:
        cli.echo(output.rstrip())
    return result.returncode, output


# Candidates whose installed binary can be executed cheaply to prove it matches this machine.
_RUN_CHECK: dict[str, list[str]] = {"java": ["bin/java", "-version"]}


def _candidate_runs(candidate: str, identifier: str) -> bool:
    """Whether the installed `candidate`/`identifier` actually executes (a wrong-architecture JDK
    fails with "Bad CPU type in executable"). Candidates without a cheap probe count as fine."""
    probe = _RUN_CHECK.get(candidate)
    if probe is None:
        return True
    exe = _sdkman_dir() / "candidates" / candidate / identifier / probe[0]
    if not exe.is_file():
        return False
    try:
        result = subprocess.run([str(exe), *probe[1:]], capture_output=True, check=False, timeout=30)
    except OSError, subprocess.TimeoutExpired:
        return False
    return result.returncode == 0


def _broken_pins(repo_path: Path) -> dict[str, str]:
    """The `.sdkmanrc` pins that are installed (dir exists) but cannot execute."""
    return {
        candidate: identifier
        for candidate, identifier in read_sdkmanrc(repo_path).items()
        if (_sdkman_dir() / "candidates" / candidate / identifier).is_dir()
        and not _candidate_runs(candidate, identifier)
    }


def _remove_install(candidate: str, identifier: str) -> None:
    shutil.rmtree(_sdkman_dir() / "candidates" / candidate / identifier, ignore_errors=True)


def _failed_pins(repo_path: Path) -> dict[str, str]:
    """The `.sdkmanrc` pins that are not installed (no `~/.sdkman/candidates/<candidate>/<id>` dir) —
    i.e. the ones a failed `sdk env install` could not install (corrupt archive, bad release...)."""
    return {
        candidate: identifier
        for candidate, identifier in read_sdkmanrc(repo_path).items()
        if not (_sdkman_dir() / "candidates" / candidate / identifier).is_dir()
    }


def _skip_and_repin(repo_path: Path, candidate: str, bad: str, reason: str = "") -> str | None:
    """Append `# sdkman-skip: <candidate> <bad>  # <reason>` to `.sdkmanrc` and re-pin `candidate` to
    the newest non-skipped, non-pre-release identifier `sdk list` offers in the same channel. Returns
    the new identifier, or `None` when there is none (the skip line is still written)."""
    path = repo_path / ".sdkmanrc"
    lines = path.read_text(encoding="utf-8").splitlines()
    skip_line = f"# sdkman-skip: {candidate} {bad}" + (f"  # {reason}" if reason else "")
    if not any(line.startswith(f"# sdkman-skip: {candidate} {bad}") for line in lines):
        lines.append(skip_line)
    skip = read_skip_list(repo_path).get(candidate, set()) | {bad}
    replacement = latest_identifier(candidate, f"0.0.0{_channel_suffix(bad)}", skip)
    if replacement:
        lines = [f"{candidate}={replacement}" if line.strip().startswith(f"{candidate}=") else line for line in lines]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return replacement


def _finish_retry(repo_path: Path) -> None:
    """The single retry after a re-pin; the result must be installed and runnable."""
    info("Retrying sdk env install once...")
    code, _output = _run_sdk_env_install(repo_path)
    if code == 0 and not _broken_pins(repo_path):
        success("SDKMAN toolchain installed after re-pinning")
    else:
        warning("sdk env install still failing after the re-pin — check `sdk env` output")


def sdkman_env_install(repo_path: Path) -> None:
    """`sdk env install` in `repo_path` — installs whatever `.sdkmanrc` pins (the pins are set by
    `/update`, i.e. `python -m modules.fireball_ai_toolkit.versioning.sdkman`). `sdk` is a shell function, so
    this goes through a login shell that sources sdkman-init.sh (native arm64 on Apple Silicon).

    Self-repairing, one retry:
    - an installed pin that cannot execute (e.g. an x86_64 JDK on arm64 without Rosetta) is removed
      and reinstalled natively; if it still cannot run it is recorded as a `# sdkman-skip:` line
      with the reason and re-pinned to the next newest identifier;
    - a pin that did not install (corrupt archive, bad release...) is skipped and re-pinned too."""
    info("Installing .sdkmanrc toolchain via SDKMAN...")
    ensure_native_sdkman_platform()
    for candidate, identifier in _broken_pins(repo_path).items():
        warning(f"{candidate} {identifier} is installed but cannot run (wrong architecture?); removing it to reinstall")
        _remove_install(candidate, identifier)
    code, _output = _run_sdk_env_install(repo_path)

    broken = _broken_pins(repo_path)
    if broken:
        for candidate, identifier in broken.items():
            _remove_install(candidate, identifier)
            replacement = _skip_and_repin(
                repo_path, candidate, identifier, "installed but cannot execute on this machine"
            )
            warning(
                f"{candidate} {identifier} still cannot run after a native reinstall; skipped, re-pinned to {replacement}"
            )
        _finish_retry(repo_path)
        return
    if code == 0:
        success("SDKMAN toolchain installed")
        return

    failed = _failed_pins(repo_path)
    if not failed:
        warning("sdk env install completed with warnings — check `sdk env` output")
        return
    for candidate, bad in failed.items():
        replacement = _skip_and_repin(repo_path, candidate, bad)
        if replacement:
            warning(f"SDKMAN could not install {candidate} {bad}; skipped it and re-pinned to {replacement}")
        else:
            warning(f"SDKMAN could not install {candidate} {bad}; skipped it, no other release to re-pin to")
    _finish_retry(repo_path)


def rust_install(repo_path: Path, version: str) -> None:
    """Install the exact Rust version `rust-toolchain.toml` pins into the repo-local `.rust/` (rustup is bootstrapped
    there if missing), and uninstall superseded toolchains. Never touches ~/.rustup or ~/.cargo."""
    info(f"Installing Rust {version} into .rust/ ...")
    if install_pinned(repo_path, version):
        success(f"Rust {version} installed (repo-local .rust/)")
    else:
        error(f"Rust {version} install failed — see the output above")


def _print_summary(
    *,
    upgrade_uv: bool,
    upgrade_python: bool,
    upgrade_libs: bool,
    upgrade_sdkman: bool,
    rust_pin: str | None,
    python_only: bool,
    libs_only: bool,
    python_current: str,
    python_latest: str,
    libs_count: int,
) -> list[str]:
    """Print the "what will change" block; return the list of items to be upgraded."""
    cli.echo("\n" + "=" * 60)
    cli.echo("🚀 UPGRADE SUMMARY")
    cli.echo("=" * 60)

    will_upgrade: list[str] = []
    if upgrade_uv:
        cli.echo("\n⚡ uv binary: refresh to latest (unpinned)")
        will_upgrade.append("uv")
    if upgrade_python:
        cli.echo(f"\n🐍 Python: {python_current} → {python_latest}")
        cli.echo("   Actions:\n   - Install new Python version\n   - Rebuild .venv")
        will_upgrade.append("Python")
    elif python_only:
        cli.echo(f"\n🐍 Python: {python_current} (already up to date)")

    if upgrade_libs:
        cli.echo(f"\n📦 Libraries: {libs_count} updates available")
        cli.echo("   Actions:\n   - Run uv sync --upgrade")
        will_upgrade.append(f"{libs_count} libraries")
    elif libs_only:
        cli.echo("\n📦 Libraries: Already up to date")

    if upgrade_sdkman:
        cli.echo("\n☕ SDKMAN toolchain: .sdkmanrc present")
        cli.echo("   Actions:\n   - Run sdk env install (installs whatever .sdkmanrc pins)")
        will_upgrade.append("SDKMAN toolchain")

    if rust_pin:
        cli.echo(f"\n🦀 Rust toolchain: rust-toolchain.toml pins {rust_pin}")
        cli.echo("   Actions:\n   - Install it into the repo-local .rust/ (rustup bootstrapped if missing)")
        cli.echo("   - Uninstall superseded toolchains")
        will_upgrade.append("Rust toolchain")

    return will_upgrade


def _print_final(
    *,
    upgrade_uv: bool,
    upgrade_python: bool,
    upgrade_libs: bool,
    upgrade_sdkman: bool,
    rust_pin: str | None,
    python_latest: str,
    libs_count: int,
) -> None:
    """Print the closing "done" block."""
    cli.echo("\n" + "=" * 60)
    success("Upgrade complete!")
    if upgrade_uv:
        cli.echo("\n✅ uv binary refreshed")
    if upgrade_python:
        cli.echo(f"\n✅ Python upgraded to {python_latest}\n✅ Virtual environment rebuilt")
    if upgrade_libs:
        cli.echo(f"\n✅ {libs_count} libraries updated")
    if upgrade_sdkman:
        cli.echo("\n✅ SDKMAN toolchain installed (`sdk env` to activate in a shell)")
    if rust_pin:
        cli.echo(f"\n✅ Rust {rust_pin} installed in .rust/ (the orchestrator's tasks use it automatically)")
    cli.echo("\n💡 Changes installed and ready to use\n")


@cli.command()
@cli.option("--only", help="Upgrade just one toolchain: uv | python | libs | sdkman | rust")
@cli.option("--sync", "sync_only", is_flag=True, help="Only run `uv sync --upgrade` (no version checks)")
@cli.option("--yes", "-y", "no_confirm", is_flag=True, help="Skip confirmation")
def main(only: str | None, sync_only: bool, no_confirm: bool) -> None:
    """
    Execute the toolchain upgrades reviewed via /update.

    Performs actual installations:
    - Refreshes the uv binary itself (unpinned — brew, or `uv self update`)
    - Downloads and installs the pinned Python version, rebuilds .venv if it changed
    - Runs uv sync --upgrade to install updated dependencies
    - Runs `sdk env install` for the .sdkmanrc toolchain
    - Installs the exact Rust in rust-toolchain.toml into the repo-local .rust/ (only in the repo that owns it)

    IMPORTANT: Run /update first to update config files before upgrading.

    Examples:
        /upgrade                  # Upgrade every detected toolchain (+ refresh uv)
        /upgrade uv               # Only the uv binary
        /upgrade python           # Only Python
        /upgrade libs             # Only libraries
        /upgrade sdkman           # Only the .sdkmanrc toolchain
        /upgrade rust             # Only the pinned Rust toolchain (.rust/)
        /upgrade --sync           # Just `uv sync --upgrade`
        /upgrade --yes            # Skip confirmation
    """
    repo_path = get_repo_local()

    if sync_only:
        run_uv_sync()
        return

    if only and only not in ("uv", "python", "libs", "sdkman", "rust"):
        cli.echo(f"Unknown target {only!r} — pick one of: uv, python, libs, sdkman, rust", err=True)
        raise SystemExit(2)
    scoped = bool(only)  # any --only <x> means "just that one"

    # No pyproject.toml → not a Python repo (e.g. a `--repo` target that's a Kotlin app). The
    # Python / libs branches don't apply; only the uv binary / a .sdkmanrc toolchain might.
    has_pyproject = (repo_path / "pyproject.toml").exists()

    # Determine what to upgrade
    upgrade_uv = (only == "uv") or not scoped
    upgrade_python = (only == "python" or not scoped) and has_pyproject
    upgrade_libs = (only == "libs" or not scoped) and has_pyproject
    python_only = only == "python"
    libs_only = only == "libs"

    # Check what needs upgrading
    if has_pyproject:
        python_needs_upgrade, python_current, python_latest = check_python_needs_upgrade(repo_path)
        libs_need_upgrade, libs_count = check_libs_need_upgrade(repo_path)
    else:
        python_needs_upgrade, python_current, python_latest = (False, "", "")
        libs_need_upgrade, libs_count = (False, 0)
    # SDKMAN toolchain — the full `upgrade` or `--only sdkman`, and only when a `.sdkmanrc` exists.
    # `/update` has already rewritten the pins by now; this just installs them.
    upgrade_sdkman = (only == "sdkman" or not scoped) and bool(read_sdkmanrc(repo_path))

    # Rust — only in the repo that owns the pin (rust-toolchain.toml, no root Cargo.toml), and only when the exact
    # pinned version is not installed repo-locally yet. `/update` has already moved the pin.
    rust_pin = read_pin(repo_path) if (only == "rust" or not scoped) and owns_rust(repo_path) else None
    if rust_pin and is_installed(repo_path, rust_pin):
        if only == "rust":
            cli.echo(f"\n🦀 Rust: {rust_pin} already installed in .rust/")
        rust_pin = None

    # Filter based on flags
    if upgrade_python and not python_needs_upgrade:
        upgrade_python = False
    if upgrade_libs and not libs_need_upgrade:
        upgrade_libs = False

    # === Display Summary ===
    will_upgrade = _print_summary(
        upgrade_uv=upgrade_uv,
        upgrade_python=upgrade_python,
        upgrade_libs=upgrade_libs,
        upgrade_sdkman=upgrade_sdkman,
        rust_pin=rust_pin,
        python_only=python_only,
        libs_only=libs_only,
        python_current=python_current,
        python_latest=python_latest,
        libs_count=libs_count,
    )

    if not will_upgrade:
        cli.echo("\n" + "=" * 60)
        success("Everything is already up to date!")
        cli.echo("\n💡 Nothing to upgrade")
        raise SystemExit(0)

    # === Confirmation ===
    if not no_confirm:
        cli.echo("\n" + "=" * 60)
        upgrade_summary = " and ".join(will_upgrade)

        if not cli.confirm(f"💡 Proceed with upgrading {upgrade_summary}?"):
            cli.echo("Cancelled.")
            raise SystemExit(2)

    # === Execute Upgrades ===
    cli.echo("\n" + "=" * 60)
    cli.echo("⚙️  EXECUTING UPGRADES...")
    cli.echo("=" * 60)

    if upgrade_uv:
        cli.echo("\n⚡ Refreshing uv...")
        upgrade_uv_binary()

    # Python upgrade (includes venv rebuild)
    if upgrade_python:
        cli.echo(f"\n🐍 Upgrading Python to {python_latest}...")
        rebuild_venv(repo_path, python_latest)

    # Libraries upgrade (or just sync if Python was upgraded)
    if upgrade_libs or upgrade_python:
        cli.echo("\n📦 Syncing dependencies...")
        run_uv_sync()

    if upgrade_sdkman:
        cli.echo("\n☕ Installing SDKMAN toolchain...")
        sdkman_env_install(repo_path)

    if rust_pin:
        cli.echo("\n🦀 Installing Rust toolchain...")
        rust_install(repo_path, rust_pin)

    _print_final(
        upgrade_uv=upgrade_uv,
        upgrade_python=upgrade_python,
        upgrade_libs=upgrade_libs,
        upgrade_sdkman=upgrade_sdkman,
        rust_pin=rust_pin,
        python_latest=python_latest,
        libs_count=libs_count,
    )


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
