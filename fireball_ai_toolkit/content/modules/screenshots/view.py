"""Copy latest screenshot to latest.png for AI access."""

import argparse
import shutil
import subprocess

from ..common import cli
from ..common.utils import error, success, warning
from ..setup.properties import get_screenshots_latest_file, get_screenshots_location


def main() -> None:
    """
    Copy the most recent screenshot to screenshots/latest.png.

    This allows AI agents to access the latest screenshot without
    dealing with filenames that contain spaces.
    """
    screenshots_dir = get_screenshots_location()
    latest_filename = get_screenshots_latest_file()

    if not screenshots_dir.exists():
        error(f"Screenshots directory not found: {screenshots_dir}")

    # Find most recent screenshot (excluding latest.png itself)
    patterns = ["*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG"]
    all_screenshots = []

    for pattern in patterns:
        all_screenshots.extend(screenshots_dir.glob(pattern))

    # Filter out latest.png
    all_screenshots = [f for f in all_screenshots if f.name != latest_filename]

    if not all_screenshots:
        warning("No screenshots found")
        return

    # Sort by modification time (newest first)
    latest_screenshot = max(all_screenshots, key=lambda p: p.stat().st_mtime)

    # Copy to latest.png
    dest = screenshots_dir / latest_filename
    shutil.copy2(latest_screenshot, dest)

    # Auto-resize if too large for AI context window (> 1 MB)
    size_mb = dest.stat().st_size / (1024 * 1024)
    if size_mb > 1.0:
        subprocess.run(
            ["sips", "-Z", "1000", str(dest)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        new_size_mb = dest.stat().st_size / (1024 * 1024)
        cli.echo(f"🔬 Resized: {size_mb:.1f} MB → {new_size_mb:.1f} MB")

    success(f"Latest screenshot copied to: {latest_filename}")
    cli.echo(f"📸 Source: {latest_screenshot.name}")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Copy latest screenshot to latest.png")
    return parser.parse_args()


if __name__ == "__main__":
    parse_args()
    main()
