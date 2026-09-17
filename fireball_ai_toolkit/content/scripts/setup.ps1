# Windows setup — mirrors setup.sh (macOS/Linux). Run from the repo root in PowerShell:
#   .\setup.ps1
#
# Clobbered by `invoke ai_toolkit.download` — DO NOT EDIT. Repo-specific setup goes in
# setup.local.ps1 (git-tracked, never clobbered), which this script dot-sources if present.

$ErrorActionPreference = "Stop"

function Install-Tools {
    Write-Host "INFO: Installing Tools (uv, user-local install — no admin required)"
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "INFO: uv already installed"
    } else {
        irm https://astral.sh/uv/install.ps1 | iex
    }
}

# Dot-source setup.local.ps1 once, then run its `Setup-Local-<Phase>` function if defined.
# Phases: `Tools` (after the tool install, before the venv) and `Post` (after properties.yml).
$script:LocalHookSourced = $false
function Invoke-LocalHook {
    param([string]$Phase)
    if (-not (Test-Path "setup.local.ps1")) { return }
    if (-not $script:LocalHookSourced) { . ./setup.local.ps1; $script:LocalHookSourced = $true }
    $fn = "Setup-Local-$Phase"
    if (Get-Command $fn -ErrorAction SilentlyContinue) {
        Write-Host "`nINFO: setup.local.ps1 -> $fn"
        & $fn
    }
}

function Setup-PythonEnv {
    Write-Host "`nINFO: Creating Python Virtual Environment"
    uv venv .venv --python 3.14 --clear

    Write-Host "`nINFO: Activating Python Virtual Environment"
    & .\.venv\Scripts\Activate.ps1

    Write-Host "`nINFO: Installing Libraries"
    uv sync
    Write-Host "INFO: Python Version: $(python --version)"
    Write-Host "INFO: uv Version: $(uv --version)"
}

function Configure-Properties {
    # Everything past this point is Python's job, not PowerShell's.
    Write-Host "`nINFO: Configuring properties.yml for this machine"
    uv run --no-sync invoke setup.properties
}

Install-Tools
Invoke-LocalHook Tools
Setup-PythonEnv
Configure-Properties
Invoke-LocalHook Post
