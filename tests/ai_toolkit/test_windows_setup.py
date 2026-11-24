"""Exercise Windows bootstrap phases without installing tools or touching the user's profile."""

import os
import shutil
import subprocess

import pytest

from fireball_ai_toolkit.catalog import packaged_content_root


def test_windows_setup_ascii():
    """Without a BOM, PS5.1 treats UTF-8 punctuation as ANSI syntax characters."""
    (packaged_content_root() / "scripts/setup.ps1").read_bytes().decode("ascii")


@pytest.mark.parametrize("failed_step", ["", "venv", "sync", "setup.properties"])
def test_windows_setup_hooks_and_failures(tmp_path, failed_step):
    shell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not shell:
        pytest.skip("PowerShell required")
    shutil.copy2(packaged_content_root() / "scripts/setup.ps1", tmp_path / "setup.ps1")
    (tmp_path / "setup.local.ps1").write_text(
        "$global:sourced++\n"
        "function Setup-Local-Tools { $global:steps.Add('tools') }\n"
        "function Setup-Local-Post { $global:steps.Add('post') }\n",
        encoding="ascii",
    )
    (tmp_path / "test.ps1").write_text(
        """$ErrorActionPreference = 'Stop'
$global:steps = [System.Collections.Generic.List[string]]::new()
$global:sourced = 0
function uv {
    if ($env:PYTHONUTF8 -ne '1' -or $env:PYTHONIOENCODING -ne 'utf-8') { throw 'Python must use UTF-8 before bootstrap commands' }
    $global:LASTEXITCODE = 0
    $global:steps.Add(($args -join ' '))
    if ($env:FAILED_STEP -and ($args -contains $env:FAILED_STEP)) { $global:LASTEXITCODE = 7 }
}
$caught = $false
try { . ./setup.ps1 } catch {
    if ($_.Exception.Message -notlike '*failed (7)*') { throw }
    $caught = $true
}
if ($global:sourced -ne 1 -or $global:steps[0] -ne 'tools') { throw 'Tools hook must run once before venv' }
if ($env:FAILED_STEP) {
    if (-not $caught -or $global:steps.Contains('post')) { throw 'Bootstrap must stop after native command failure' }
} elseif ($caught -or $global:steps[$global:steps.Count - 1] -ne 'post') { throw 'Post hook must run last' }
Write-Host 'PASS: bootstrap phase ordering and native exit handling'
""",
        encoding="ascii",
    )
    result = subprocess.run(
        [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "test.ps1"],
        cwd=tmp_path,
        env={**os.environ, "FAILED_STEP": failed_step},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("venv_fails", [1, 2])
def test_windows_setup_updates_uv_when_the_pinned_python_is_unknown(tmp_path, venv_fails):
    """An older uv cannot find a newer pinned Python: update uv once and retry; fail clearly if it still cannot."""
    shell = shutil.which("powershell.exe") or shutil.which("pwsh")
    if not shell:
        pytest.skip("PowerShell required")
    shutil.copy2(packaged_content_root() / "scripts/setup.ps1", tmp_path / "setup.ps1")
    (tmp_path / ".python-version").write_text("3.99.9\n", encoding="ascii")
    (tmp_path / "test.ps1").write_text(
        """$ErrorActionPreference = 'Stop'
$global:steps = [System.Collections.Generic.List[string]]::new()
$global:venvCalls = 0
function uv {
    $global:LASTEXITCODE = 0
    $global:steps.Add(($args -join ' '))
    if ($args[0] -eq 'venv') {
        $global:venvCalls++
        if ($global:venvCalls -le [int]$env:VENV_FAILS) { $global:LASTEXITCODE = 2 }
    }
}
$caught = ''
try { . ./setup.ps1 } catch { $caught = $_.Exception.Message }
if ($env:VENV_FAILS -eq '1') {
    if ($caught) { throw "one failed venv must be retried after the update, got: $caught" }
    if (-not $global:steps.Contains('self update')) { throw 'uv must be updated before the retry' }
    if ($global:venvCalls -ne 2) { throw 'venv must be tried exactly twice' }
} else {
    if ($caught -notlike '*not available to uv*') { throw "a second failure must say what to do, got: $caught" }
    if ($global:venvCalls -ne 2) { throw 'venv must not be retried more than once' }
}
Write-Host 'PASS: uv update and retry'
""",
        encoding="ascii",
    )
    result = subprocess.run(
        [shell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "test.ps1"],
        cwd=tmp_path,
        env={**os.environ, "VENV_FAILS": str(venv_fails)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_unix_setup_updates_uv_when_the_pinned_python_is_unknown(tmp_path):
    """setup.sh retries once after updating uv (a stub uv fails the first venv call and records `self update`)."""
    bash = shutil.which("bash")
    if not bash:
        pytest.skip("bash required")
    bindir = tmp_path / "bin"
    bindir.mkdir()
    uv = bindir / "uv"
    uv.write_text(
        '#!/bin/bash\necho "$*" >> "$LOG"\n'
        'if [ "$1" = venv ]; then n=$(grep -c "^venv" "$LOG"); [ "$n" -le 1 ] && exit 2; fi\nexit 0\n',
        encoding="ascii",
    )
    uv.chmod(0o755)
    script = (packaged_content_root() / "scripts/setup.sh").read_text(encoding="utf-8")
    # Run only setup_python_env: stop before the virtual-environment activation, which needs a real venv.
    harness = tmp_path / "harness.sh"
    functions = script.split("setup_python_env() {")[0]
    start = functions.index("update_uv() {")
    harness.write_text(
        "set -u\n"
        + functions[start:]
        + 'echo "3.99.9" > .python-version\n'
        + "python_pin=3.99.9\n"
        + 'if ! uv venv .venv --python "${python_pin}" --clear; then update_uv; uv venv .venv --python "${python_pin}" --clear; fi\n',
        encoding="utf-8",
    )
    log = tmp_path / "log.txt"
    log.write_text("")
    result = subprocess.run(
        [bash, str(harness)],
        cwd=tmp_path,
        env={**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "LOG": str(log)},
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    calls = log.read_text().splitlines()
    assert [c.split()[0] + " " + (c.split()[1] if len(c.split()) > 1 else "") for c in calls][:3] == ["venv .venv", "self update", "venv .venv"]
