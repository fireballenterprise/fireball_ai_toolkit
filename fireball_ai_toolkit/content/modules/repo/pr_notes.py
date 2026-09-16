"""Save Pull Request notes markdown to tmp/pull_requests/."""

from __future__ import annotations

from datetime import UTC, datetime

from ..common import cli as click
from ..common.utils import error, success
from ..setup.properties import get_repo_local
from .pr_diff import current_branch


@click.command()
@click.option("--content", default=None, help="Markdown PR notes content")
def main(content: str | None = None) -> None:
    """Save PR notes markdown to tmp/pull_requests/<timestamp>_<branch>.md."""
    if not content or not content.strip():
        error("PR notes content cannot be empty")

    repo_path = get_repo_local()
    branch = current_branch(repo_path)
    safe_branch = branch.replace("/", "-")

    out_dir = repo_path / "tmp" / "pull_requests"
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%SZ")
    out_file = out_dir / f"{timestamp}_{safe_branch}.md"
    out_file.write_text(content.strip() + "\n", encoding="utf-8")

    success(f"Saved PR notes: tmp/pull_requests/{out_file.name}")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
