"""`backlog.add` — open a GitHub Issue on a family repo.

uv run --no-sync python -m modules.toolkit.backlog.add --repo vscode --type bug --title "..."
"""

from __future__ import annotations

from ..common import cli
from ..common.utils import success
from .common import area_for_repo, create_issue, gh, nwo, resolve_repo, scrub, with_images


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


@cli.command()
@cli.option("--repo", required=True, help="Target family repo (fuzzy name, e.g. 'vscode')")
@cli.option(
    "--type", "issue_type", required=True, type=cli.Choice(["bug", "feature", "task"]), help="bug | feature | task"
)
@cli.option("--title", required=True, help="Issue title")
@cli.option("--body", default="", help="Issue body (markdown)")
@cli.option("--images", default="", help="Space-separated image paths to upload + embed")
@cli.option(
    "--area",
    "areas",
    default="",
    help="Comma-separated area labels — module / component / topic (added to the repo's own area)",
)
@cli.option(
    "--label", "extra_labels", default="", help="Comma-separated nature labels (e.g. Regression, Usage Failure, UI)"
)
@cli.option("--web", is_flag=True, help="Open the browser create form instead of filing directly")
def main(
    repo: str,
    issue_type: str,
    title: str,
    body: str = "",
    images: str = "",
    areas: str = "",
    extra_labels: str = "",
    web: bool = False,
) -> None:
    """File the issue and print its URL. The native issue Type carries bug/feature/task; labels
    are the repo's area plus any finer area / nature you pass."""
    target = resolve_repo(repo)
    repo_nwo = nwo(target)
    labels = list(dict.fromkeys([area_for_repo(target), *_split(areas), *_split(extra_labels)]))

    if web:
        gh(["issue", "create", "--web", "--title", title, "--label", ",".join(labels)], repo=repo_nwo)
        return

    body = with_images(repo_nwo, scrub(body), images)
    url = create_issue(repo_nwo, title=title, body=body or title, issue_type=issue_type, labels=labels)
    success(f"filed {repo_nwo} ({issue_type}) [{', '.join(labels)}]: {url}")


if __name__ == "__main__":
    main()
