"""Invoke task runner that ensures execution from repository root."""

import os
from pathlib import Path

from ..setup.properties import get_repo_local


def run_from_root(ctx, command: str, **kwargs):
    """
    Execute command from repository root, regardless of current directory.

    This ensures all Python module imports work correctly by running from
    the directory containing the modules/ package.

    Uses repo root from properties.yml for consistency.

    Args:
        ctx: Invoke context object
        command: Command to execute
        **kwargs: Additional arguments passed to ctx.run()

    Example:
        >>> run_from_root(ctx, 'uv run python -m modules.toolkit.topic.init')
    """
    # Record original working directory
    original_cwd = Path.cwd()

    # Get repository root from properties.yml
    repo_root = get_repo_local()

    # Store original CWD in environment variable for scripts to access
    env = kwargs.pop("env", None) or {}
    env["AI_VAULT_ORIGINAL_CWD"] = str(original_cwd)

    # Change to repo root and execute
    with ctx.cd(str(repo_root)):
        return ctx.run(command, env=env, **kwargs)


def get_original_cwd() -> Path:
    """
    Get original working directory from environment or current directory.

    When called from scripts invoked via run_from_root(), returns the directory
    where the user originally invoked the command.

    Returns:
        Path to original working directory.

    Example:
        >>> original_dir = get_original_cwd()
        >>> if "/topics/" in str(original_dir):
        >>>     print(f"User is in topic: {original_dir}")
    """
    original_cwd = os.environ.get("AI_VAULT_ORIGINAL_CWD")
    if original_cwd:
        return Path(original_cwd)
    return Path.cwd()
