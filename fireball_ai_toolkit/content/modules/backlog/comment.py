"""`backlog.comment` — add a comment to an issue (progress notes, findings, "blocked on ...").

uv run --no-sync python -m modules.toolkit.backlog.comment --repo vscode --number 12 --body "..."
"""

from __future__ import annotations

from ..common import cli
from ..common.utils import success
from .common import gh, nwo, resolve_repo, scrub, with_images


@cli.command()
@cli.option("--repo", required=True, help="Family repo (fuzzy name)")
@cli.option("--number", required=True, type=int, help="Issue number")
@cli.option("--body", required=True, help="Comment body (markdown)")
@cli.option("--images", default="", help="Space-separated image paths to upload + embed")
def main(repo: str, number: int, body: str, images: str = "") -> None:
    """Post the comment."""
    repo_nwo = nwo(resolve_repo(repo))
    text = with_images(repo_nwo, scrub(body), images)
    gh(["issue", "comment", str(number), "--body", text], repo=repo_nwo)
    success(f"commented on {repo_nwo}#{number}")


if __name__ == "__main__":
    main()
