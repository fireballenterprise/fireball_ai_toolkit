"""Open a GitHub Pull Request for the current branch via gh."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..common import cli as click
from ..common.utils import error, success, warning
from ..setup.properties import FamilyRepo, find_current_repo, get_repo_local
from .pr_diff import current_branch, detect_base_branch


def _last_line(text: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _link_issue(repo_path: Path, self_repo: FamilyRepo | None, issue: int, pr_url: str) -> None:
    """Best-effort: comment the PR link back onto the issue. Never fails the PR creation — the
    PR body's `Tracks #<issue>` line already gives GitHub's own cross-reference either way."""
    if self_repo is None:
        warning(f"can't resolve this repo's org/name — skipping the #{issue} comment (PR still created)")
        return
    repo_nwo = f"{self_repo.org}/{self_repo.name}"
    result = subprocess.run(
        ["gh", "issue", "comment", str(issue), "--repo", repo_nwo, "--body", f"PR: {pr_url}"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        warning(f"couldn't comment on {repo_nwo}#{issue} (PR still created): {result.stderr.strip()}")
        return
    click.echo(f"Linked to {repo_nwo}#{issue}")


@click.command()
@click.option("--title", default=None, help="Pull request title")
@click.option("--content", default=None, help="Pull request body (markdown)")
@click.option(
    "--issue",
    default=None,
    type=int,
    help="Issue number (this repo) this PR tracks — noted in the PR body and linked back from the issue",
)
def main(title: str | None = None, content: str | None = None, issue: int | None = None) -> None:
    """Open a GitHub PR for the current branch against its detected base branch."""
    self_repo = find_current_repo()
    if self_repo is not None and not self_repo.pull_request:
        error(
            f"{self_repo.name} ships by direct push (pull_request: false in properties.yml) — "
            "not opening a PR. Fast-forward the default branch to your work and push instead."
        )
    if not title or not title.strip():
        error("PR title cannot be empty")
    if not content or not content.strip():
        error("PR notes content cannot be empty")

    repo_path = get_repo_local()
    branch = current_branch(repo_path)
    base_ref = detect_base_branch(repo_path, branch)
    base_name = base_ref.removeprefix("origin/")

    body = f"{content.rstrip()}\n\nTracks #{issue}" if issue else content

    click.echo(f"Creating PR: {branch} -> {base_name}")
    result = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--base",
            base_name,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            body,
            "--assignee",
            "@me",
        ],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        if "already exists" in result.stderr.lower():
            existing = subprocess.run(
                ["gh", "pr", "view", "--json", "url", "-q", ".url"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if existing.returncode == 0 and existing.stdout.strip():
                pr_url = existing.stdout.strip()
                success(f"PR already exists: {pr_url}")
                if issue:
                    _link_issue(repo_path, self_repo, issue, pr_url)
                return
        error(f"gh pr create failed:\n{result.stderr}")

    pr_url = _last_line(result.stdout)
    success("PR created!")
    click.echo(pr_url or result.stdout.strip())
    if issue and pr_url:
        _link_issue(repo_path, self_repo, issue, pr_url)


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
