"""Docs automation tasks — changelog sync from properties.yml, etc. See
`.github/instructions/changelogs.instructions.md`.
"""

from invoke import task


@task
def update_changelogs(context):
    """Prepend any missing docs/change_logs/<category>/<name>.md entries from properties.yml."""
    context.run("uv run --no-sync python -m modules.toolkit.docs.update", pty=True)
