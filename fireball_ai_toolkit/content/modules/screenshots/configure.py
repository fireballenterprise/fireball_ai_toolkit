"""Configure macOS screenshot location to central repository folder."""

import subprocess

from ..common import cli as click
from ..common.utils import info, success
from ..setup.properties import get_repo_local, get_screenshots_location


@click.command()
def main() -> None:
    """
    Configure macOS to save screenshots to the central repo screenshots folder.

    Updates macOS default screenshot location and restarts SystemUIServer.
    """
    repo_root = get_repo_local()
    screenshot_dir = get_screenshots_location()

    click.echo("🎯 Setting macOS screenshot location to central repo folder")
    click.echo()
    info(f"Repository root: {repo_root}")

    # Ensure screenshots directory exists
    click.echo("📸 Ensuring screenshots directory exists...")
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    # Update macOS screenshot location
    click.echo("⚙️  Updating macOS screenshot location...")
    try:
        subprocess.run(
            ["defaults", "write", "com.apple.screencapture", "location", str(screenshot_dir)],
            check=True,
        )
        subprocess.run(
            ["killall", "SystemUIServer"],
            check=False,  # Don't fail if SystemUIServer isn't running
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to configure screenshot location: {e}", err=True)
        raise SystemExit(1) from e

    # Disable floating thumbnail preview
    click.echo("🔇 Disabling screenshot thumbnail preview...")
    try:
        subprocess.run(
            ["defaults", "write", "com.apple.screencapture", "show-thumbnail", "-bool", "false"],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Failed to disable thumbnail preview: {e}", err=True)
        raise SystemExit(1) from e

    click.echo()
    success(f"Screenshot location configured: {screenshot_dir}")
    success("Floating thumbnail preview disabled")
    click.echo()
    click.echo("💡 All new screenshots will save here. Use 'ss' to view the latest screenshot.")


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
