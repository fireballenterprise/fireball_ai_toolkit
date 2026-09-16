"""`backlog.close` — close an issue, optionally noting what fixed it first.

uv run --no-sync python -m modules.toolkit.backlog.close --repo vscode --number 12 --pr 45
"""

from __future__ import annotations

from ..common import cli
from ..common.utils import success
from .common import gh, nwo, resolve_repo, scrub

_REASONS = {"completed": "completed", "not-planned": "not planned"}


@cli.command()
@cli.option("--repo", required=True, help="Family repo (fuzzy name)")
@cli.option("--number", required=True, type=int, help="Issue number")
@cli.option("--pr", default="", help="PR number that fixed it (adds a 'Fixed in #<pr>' note)")
@cli.option("--sha", default="", help="Commit sha that fixed it (direct-push repos)")
@cli.option("--reason", default="completed", type=cli.Choice(["completed", "not-planned"]), help="Close reason")
@cli.option("--comment", "note", default="", help="Extra free-text note to post before closing")
def main(repo: str, number: int, pr: str = "", sha: str = "", reason: str = "completed", note: str = "") -> None:
    """Post the fix note (if any), then close."""
    repo_nwo = nwo(resolve_repo(repo))
    fixed = f"Fixed in {repo_nwo}#{pr}" if pr else (f"Fixed in {sha}" if sha else "")
    parts = [part for part in (fixed, scrub(note)) if part]
    if parts:
        gh(["issue", "comment", str(number), "--body", "\n\n".join(parts)], repo=repo_nwo)
    gh(["issue", "close", str(number), "--reason", _REASONS[reason]], repo=repo_nwo)
    success(f"closed {repo_nwo}#{number} ({_REASONS[reason]})")


if __name__ == "__main__":
    main()
