"""Keep docs/change_logs/<category>/<name>.md in sync with properties.yml's version/latest_changes
entries — see `.github/instructions/changelogs.instructions.md`.
"""

import fileinput
import logging
from pathlib import Path

from ...setup.properties import get_properties, get_repo_root

LOGGER = logging.getLogger(__name__)


def _changelog_categories() -> tuple[str, ...]:
    """Root properties.yml keys that own a change log under docs/change_logs/<category>/<name>.md.

    Read from properties.yml's ``changelogs:`` list (e.g. ``changelogs: [cloudformation]``); empty
    when there's no such key or no properties.yml at all — nothing to check.
    """
    try:
        return tuple(get_properties().get("changelogs", []))
    except FileNotFoundError:
        return ()


def changelog_entries() -> list[tuple[str, str, dict]]:
    """Return every properties.yml entry that owns a change log.

    Returns:
        List of (category, name, product) tuples — product is the dict holding `version` and
        `latest_changes`.
    """
    categories = _changelog_categories()
    if not categories:
        return []  # nothing to check — skip needing a properties.yml at all
    props = get_properties()
    return [
        (category, name, product)
        for category, products in props.items()
        if category in categories
        for name, product in products.items()
    ]


def expected_entry_text(category: str, name: str, product: dict) -> str:
    """Build the change log header + bullet block a properties.yml entry requires.

    Args:
        category: Root properties.yml key that owns the entry.
        name: Entry name under the category.
        product: Mapping holding `version` and `latest_changes` (author/date/description).

    Returns:
        Text block that must sit at the top of the entry's change log.
    """
    if "version" not in product:
        error_message = f"version is not in ({category}.{name}.{product})"
        raise ValueError(error_message)

    formatted_header = (
        f"## {product['version']} - {product['latest_changes']['date']} - {product['latest_changes']['author']}"
    )
    # `description` is one string — comma-separate it for multiple bullets.
    changes_list = product["latest_changes"]["description"].split(", ")
    formatted_changes = "\n".join("* " + change for change in changes_list)
    return formatted_header + "\n" + formatted_changes + "\n"


def changelog_path(category: str, name: str) -> Path:
    """Return the change log path for an entry.

    Args:
        category: Root properties.yml key that owns the entry.
        name: Entry name under the category.

    Returns:
        Path to the entry's change log markdown file.
    """
    return get_repo_root() / "docs" / "change_logs" / category / f"{name}.md"


def check_exists(filename: str | Path, text: str) -> bool:
    """Return whether `filename` already starts with `text`."""
    filepath = Path(filename)
    if not filepath.exists():
        return False
    with open(filepath, encoding="utf-8", newline="\n") as f:
        content = f.read()
        if content.startswith(text):
            return True
    return False


def prepend_text(filename: str | Path, text: str) -> None:
    """Insert `text` at the very top of `filename`, creating it (and its parent dir) if missing."""
    filepath = Path(filename)

    # If the file doesn't exist or is empty, just write the text.
    if not filepath.exists() or filepath.stat().st_size == 0:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
    else:
        # File exists and has content — prepend the text ahead of it.
        with fileinput.input(str(filepath), inplace=True) as file:
            for index, line in enumerate(file):
                if index == 0:
                    print(text)
                print(line, end="")


def entry_current(category: str, name: str, product: dict) -> bool:
    """Report whether an entry's change log already leads with its current version/latest_changes.

    Args:
        category: Root properties.yml key that owns the entry.
        name: Entry name under the category.
        product: Mapping holding `version` and `latest_changes`.

    Returns:
        True when the change log is up to date.
    """
    return check_exists(filename=changelog_path(category, name), text=expected_entry_text(category, name, product))


def check_each_log(update: bool = False) -> None:
    """Check every properties.yml changelog entry against its docs/change_logs/ file.

    With `update=False` (used by the drift test), raises `ValueError` on the first stale entry
    found. With `update=True` (used by `invoke docs.update_changelogs`), prepends any missing
    entry instead and never raises. A no-op either way when properties.yml has no `changelogs:` key.
    """
    if update:
        LOGGER.info("Checking and Updating Change Logs as Needed")
    else:
        LOGGER.info("Only Checking if the Change Logs are Updated (update=false)")

    current_category = None
    for category, name, product in changelog_entries():
        if update and category != current_category:
            print("\n############################################################")
            print(f"#  {category.upper()}")
            print("############################################################")
            current_category = category

        combined_text = expected_entry_text(category, name, product)
        if update:
            LOGGER.debug(combined_text)

        if entry_current(category, name, product):
            if update:
                print(f"Passed: ({category}/{name})")
            else:
                LOGGER.info("Passed: (%s/%s)", category, name)
        elif update:
            prepend_text(filename=changelog_path(category, name), text=combined_text)
            print(f"Updated: ({category}/{name})")
        else:
            print(
                f"\nERROR: Change Log ({category}/{name}) Needs to be Updated!\nTry running 'invoke docs.update_changelogs'\n"
            )
            LOGGER.error("Failed: (%s/%s)", category, name)
            error_message = f"Change log mismatch for {category}/{name}"
            raise ValueError(error_message)
