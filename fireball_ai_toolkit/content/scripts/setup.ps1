# Windows setup - mirrors setup.sh (macOS/Linux). Run from the repo root in PowerShell:
#   .\setup.ps1
#
# Clobbered by `invoke ai_toolkit.download` - DO NOT EDIT. Repo-specific setup goes in
# setup.local.ps1 (git-tracked, never clobbered), which this script dot-sources if present.

$ErrorActionPreference = "Stop"

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

function Setup-PythonEnv {
    Write-Host "`nINFO: Creating Python Virtual Environment"
    uv venv .venv --python 3.14 --clear
    if ($LASTEXITCODE -ne 0) { throw "uv venv failed ($LASTEXITCODE)" }

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
