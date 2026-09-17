"""`backlog.start` — begin working an issue: show it, assign it to you, and print the target
repo's ship rules + local clone path. Does not touch git — the agent drives the change.

    uv run --no-sync python -m modules.toolkit.backlog.start --repo vscode --number 12
"""

from __future__ import annotations

from ..common import cli
from .common import gh, issue_json, nwo, resolve_repo, scrub


@cli.command()
@cli.option("--repo", required=True, help="Family repo (fuzzy name)")
@cli.option("--number", required=True, type=int, help="Issue number")
@cli.option("--comment", "note", default="", help="Optional 'starting work' comment to post")
def main(repo: str, number: int, note: str = "") -> None:
    """Print the issue + ship rules and assign it to the gh user."""
    target = resolve_repo(repo)
    repo_nwo = nwo(target)
    data = issue_json(repo_nwo, number, "title,body,state,labels,url")
    labels = ", ".join(label["name"] for label in data.get("labels", [])) or "none"

    cli.echo(f"#{number}  {data['title']}  [{data['state']}]  ({labels})")
    cli.echo(data["url"])
    cli.echo("\n" + (data.get("body") or "(no body)").rstrip() + "\n")

    gh(["issue", "edit", str(number), "--add-assignee", "@me"], repo=repo_nwo, check=False)
    if note:
        gh(["issue", "comment", str(number), "--body", scrub(note)], repo=repo_nwo)

    ship = (
        "feature branch + PR (assign it to yourself), let CI run"
        if target.pull_request
        else f"commit straight to {target.default_branch or 'the default branch'} — no PR"
    )
    gate = "GitHub Actions" if target.use_ci else "local `invoke fix && invoke test`"
    cli.echo(f"ship rules for {repo_nwo}: {ship}")
    cli.echo(f"test/build gate: {gate}")
    cli.echo(f"local clone: {target.path}")
    if not target.exists:
        cli.echo("  (no local clone found — clone it before starting work)")


if __name__ == "__main__":
    main()
