"""`backlog.view` — show one issue (gh passthrough).

uv run --no-sync python -m modules.toolkit.backlog.view --repo vscode --number 12 [--json]
"""

from __future__ import annotations

from ..common import cli
from .common import gh, nwo, resolve_repo


@cli.command()
@cli.option("--repo", required=True, help="Family repo (fuzzy name)")
@cli.option("--number", required=True, type=int, help="Issue number")
@cli.option("--json", "as_json", is_flag=True, help="Emit raw gh JSON (title/body/labels/state/url)")
def main(repo: str, number: int, as_json: bool = False) -> None:
    """Print the issue."""
    args = ["issue", "view", str(number)]
    if as_json:
        args += ["--json", "number,title,body,state,labels,assignees,url,createdAt,closedAt"]
    cli.echo(gh(args, repo=nwo(resolve_repo(repo))).stdout.rstrip())


if __name__ == "__main__":
    main()
