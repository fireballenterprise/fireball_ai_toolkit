"""Cleanup screenshot files from repository."""

import subprocess

from ..common import cli as click
from ..common.utils import success, warning
from ..setup.properties import (
    get_repo_local,
    get_screenshots_latest_file,
    get_screenshots_location,
)


@click.command()
@click.option("--confirm/--no-confirm", default=True, help="Prompt for confirmation before deleting")
def main(confirm: bool) -> None:
    """
    Clean up screenshot images and video recordings from repository.

    Deletes all screenshot images and screen recordings except the latest.png
    file used by /ss command. Shows git status after cleanup.
    """
    repo_path = get_repo_local()
    screenshots_dir = get_screenshots_location()
    preserve_file = get_screenshots_latest_file()

    click.echo("🧹 Starting repository screenshot cleanup...")

    # Find screenshot files to delete
    click.echo("🔍 Scanning for screenshot files and recordings...")

    patterns = [
        "*.png",
        "*.jpg",
        "*.jpeg",
        "*.PNG",
        "*.JPG",
        "*.JPEG",
        "*.mov",
        "*.mp4",
        "*.MOV",
        "*.MP4",
    ]
    files_to_delete = []

    # Search in main screenshots directory
    if screenshots_dir.exists():
        for pattern in patterns:
            files_to_delete.extend(screenshots_dir.glob(pattern))

    # Search in topic subdirectories
    topics_dir = repo_path / "topics"
    if topics_dir.exists():
        for pattern in patterns:
            files_to_delete.extend(topics_dir.glob(f"**/screenshots/{pattern}"))

    # Filter out preserved file
    files_to_delete = [f for f in files_to_delete if f.name != preserve_file]

    if not files_to_delete:
        success("No screenshot files found. Repository is already clean!")
        return

    # Show files and calculate total size
    file_count = len(files_to_delete)
    total_size = sum(f.stat().st_size for f in files_to_delete)
    total_size_mb = total_size / (1024 * 1024)

    click.echo(f"📋 Found {file_count} screenshot files")
    click.echo(f"📏 Total size: {total_size_mb:.2f} MB")
    click.echo()

    # Show some example files
    if file_count <= 10:
        for f in files_to_delete:
            click.echo(f"   {f.relative_to(repo_path)}")
    else:
        for f in files_to_delete[:5]:
            click.echo(f"   {f.relative_to(repo_path)}")
        click.echo(f"   ... and {file_count - 5} more files")

    click.echo()

    # Confirm deletion
    if confirm:
        if not click.confirm("🗑️  Do you want to delete these screenshot files?"):
            click.echo("Cancelled.")
            return

    # Delete files
    click.echo("🗑️  Deleting screenshot files...")
    for file in files_to_delete:
        file.unlink()

    click.echo()
    success("Cleanup completed!")
    click.echo(f"   - Files deleted: {file_count}")
    click.echo("   - Screenshot directories preserved (empty)")
    click.echo(f"   - {preserve_file} preserved for /ss command")

    # Show git status
    click.echo()
    click.echo("📊 Git status (deleted files):")
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=False,
        )
        deleted_files = [line for line in result.stdout.splitlines() if line.startswith(" D")]
        for line in deleted_files[:10]:
            click.echo(f"   {line}")

        if len(deleted_files) > 10:
            click.echo(f"   ... and {len(deleted_files) - 10} more files")

        click.echo(f"   Total files staged for deletion: {len(deleted_files)}")
    except (subprocess.SubprocessError, OSError) as e:
        warning(f"Could not get git status: {e}")

    click.echo()
    click.echo("💡 Next steps:")
    click.echo("   Run '/sync' to commit and push these changes")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
