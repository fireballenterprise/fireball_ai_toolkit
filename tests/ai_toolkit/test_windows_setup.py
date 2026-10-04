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
