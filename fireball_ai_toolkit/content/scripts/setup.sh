#!/usr/bin/env bash
# Clobbered by `invoke ai_toolkit.download` — DO NOT EDIT. Repo-specific setup goes in
# setup.local.sh (git-tracked, never clobbered), which this script sources if present.
set -e

# ---------------------------------------------------------------------------
# OS-specific tool installation
# ---------------------------------------------------------------------------

install_uv_curl() {
  echo "INFO: Installing Tools (uv, user-local install — no sudo, no system package manager)"
  if command -v uv &> /dev/null; then
    echo "INFO: uv already installed"
  else
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # shellcheck disable=SC1091
    source "$HOME/.local/bin/env" 2>/dev/null || export PATH="$HOME/.local/bin:$PATH"
  fi
}

install_tools_macos() {
  if command -v brew &> /dev/null; then
    echo "INFO: Installing Tools (Homebrew)"
    brew install uv
  else
    echo "INFO: Homebrew not found — falling back to user-local install"
    install_uv_curl
  fi
}

install_tools_linux() {
  install_uv_curl
  echo "NOTE: For Windows, use setup.ps1 in PowerShell instead of this script."
}

# ---------------------------------------------------------------------------
# Repo-local hook
# ---------------------------------------------------------------------------

# Source setup.local.sh once, then run its `setup_local_<phase>` function if it defines one.
# Phases: `tools` (after the OS tool install, before the venv) and `post` (after properties.yml).
run_local_hook() {
  [ -f "setup.local.sh" ] || return 0
  # shellcheck disable=SC1091
  [ -n "${_SETUP_LOCAL_SOURCED:-}" ] || { source setup.local.sh; _SETUP_LOCAL_SOURCED=1; }
  local fn="setup_local_$1"
  if declare -F "$fn" > /dev/null; then
    echo -e
    echo "INFO: setup.local.sh -> $fn"
    "$fn"
  fi
}

# ---------------------------------------------------------------------------
# Shared steps (macOS + Linux)
# ---------------------------------------------------------------------------

setup_python_env() {
  echo -e
  echo "INFO: Creating Python Virtual Environment"
  uv venv .venv --python 3.14 --clear
  echo -e
  echo "INFO: Activating Python Virtual Environment"
  source .venv/bin/activate

  echo -e
  echo "INFO: Installing Libraries"
  uv sync
  echo "INFO: Python Version: $(python --version)"
  echo "INFO: uv Version: $(uv --version)"
}

configure_properties() {
  # Everything past this point is Python's job, not bash's.
  echo -e
  echo "INFO: Configuring properties.yml for this machine"
  uv run --no-sync invoke setup.properties
}

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

main() {
  case "$(uname)" in
    Darwin)
      install_tools_macos
      ;;
    Linux)
      install_tools_linux
      ;;
    *)
      echo "ERROR: Unsupported OS: $(uname)"
      echo "For Windows, run setup.ps1 in PowerShell instead of this script."
      exit 1
      ;;
  esac

  run_local_hook tools
  setup_python_env
  configure_properties
  run_local_hook post
}

main "$@"
