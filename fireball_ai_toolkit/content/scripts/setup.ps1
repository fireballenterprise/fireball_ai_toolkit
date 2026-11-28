# Windows setup - mirrors setup.sh (macOS/Linux). Run from the repo root in PowerShell:
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\setup.ps1
# Process-only policy for this trusted local script; enforced organization policies still apply.
#
# Clobbered by `invoke ai_toolkit.download` - DO NOT EDIT. Repo-specific setup goes in
# setup.local.ps1 (git-tracked, never clobbered), which this script dot-sources if present.

$ErrorActionPreference = "Stop"
# Python's redirected streams otherwise use the Windows ANSI codepage (often cp1252).
# Process environment only: neither user settings nor machine execution policy is changed.
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

function Install-Tools {
    Write-Host "INFO: Installing Tools (uv, user-local install - no admin required)"
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "INFO: uv already installed"
    } else {
        irm https://astral.sh/uv/install.ps1 | iex
    }
}

# Dot-source setup.local.ps1 once, then run its `Setup-Local-<Phase>` function if defined.
# Phases: `Tools` (after the tool install, before the venv) and `Post` (after properties.yml).
function Invoke-LocalHook {
    param([string]$Phase)
    $fn = "Setup-Local-$Phase"
    if (Get-Command $fn -ErrorAction SilentlyContinue) {
        Write-Host "`nINFO: setup.local.ps1 -> $fn"
        & $fn
    }
}

function Update-Uv {
    # A standalone uv updates itself; one installed by winget or another package manager says so and is left for that tool.
    uv self update
    if ($LASTEXITCODE -ne 0) {
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            Write-Host "INFO: uv self update is unavailable here; trying winget"
            winget upgrade --id astral-sh.uv --exact --accept-package-agreements --accept-source-agreements
        }
        Write-Host "WARN: could not update uv automatically (installed by another tool?)"
    }
    # Make the updated uv visible to this session.
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + $env:Path
}

function Setup-PythonEnv {
    Write-Host "`nINFO: Creating Python Virtual Environment"
    # The pin comes from .python-version (the one source /update python rewrites).
    $pythonPin = "3.14"
    if (Test-Path .python-version) {
        $fromFile = (Get-Content .python-version -Raw).Trim()
        if ($fromFile) { $pythonPin = $fromFile }
    }
    Write-Host "INFO: Python pin: $pythonPin"
    uv venv .venv --python $pythonPin --clear
    if ($LASTEXITCODE -ne 0) {
        # An older uv does not know a newer pinned Python (setup only installs uv when it is missing): update uv and retry once.
        Write-Host "INFO: uv $(uv --version) could not set up Python $pythonPin; updating uv and retrying"
        Update-Uv
        uv venv .venv --python $pythonPin --clear
        if ($LASTEXITCODE -ne 0) { throw "uv venv failed ($LASTEXITCODE): Python $pythonPin is not available to uv $(uv --version). Update uv by hand ('uv self update', or reinstall from https://astral.sh/uv) and rerun setup." }
    }

    Write-Host "`nINFO: Installing Libraries"
    uv sync
    if ($LASTEXITCODE -ne 0) { throw "uv sync failed ($LASTEXITCODE)" }
    uv run --no-sync python --version
    if ($LASTEXITCODE -ne 0) { throw "Python version check failed ($LASTEXITCODE)" }
    Write-Host "INFO: uv Version: $(uv --version)"
}

function Configure-Properties {
    # Everything past this point is Python's job, not PowerShell's.
    Write-Host "`nINFO: Configuring properties.yml for this machine"
    uv run --no-sync invoke setup.properties
    if ($LASTEXITCODE -ne 0) { throw "setup.properties failed ($LASTEXITCODE)" }
}

Install-Tools
# Source at script scope so both hook phases (and their helpers) remain available.
if (Test-Path "setup.local.ps1") { . ./setup.local.ps1 }
Invoke-LocalHook Tools
Setup-PythonEnv
Configure-Properties
Invoke-LocalHook Post
