"""``ai_toolkit.release`` — trigger the toolkit's release workflow.

The whole release (finalize VERSION, promote ``development`` -> ``main``, tag ``X.Y.Z`` +
force-move the floating major tag ``X``, publish a GitHub Release, and — once enabled — PyPI) runs
in ``.github/workflows/release.yml``. This task just dispatches it, so any repo (or the AI) can cut
a toolkit release without cloning it.

Branch model:
* ``development`` — integration; feature PRs merge here. Dev channel: pin ``...@development``.
* ``main`` — stable; only ever updated by this workflow promoting ``development``. Pin ``...@0`` while pre-1.0 (``...@1`` after launch)
  (floating major tag, no ``v`` prefix — [[versioning-no-v-prefix]]).
"""

from __future__ import annotations

import shutil
import subprocess

REPO = "fireballenterprise/fireball_ai_toolkit"
WORKFLOW = "release.yml"


def release(repo_root=None, *, ref: str = "development") -> str:  # noqa: ARG001
    """Dispatch ``release.yml`` via ``gh``. Returns the command output."""
    if shutil.which("gh") is None:
        raise RuntimeError("`gh` (GitHub CLI) is required to trigger the release workflow")
    result = subprocess.run(
        ["gh", "workflow", "run", WORKFLOW, "-R", REPO, "--ref", ref],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gh workflow run failed:\n{result.stderr.strip()}")
    return f"Release workflow dispatched for {REPO} ({ref}).\nWatch: gh run list -R {REPO} --workflow {WORKFLOW}"
