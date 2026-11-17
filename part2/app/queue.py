
"""Queue stored as one name per line.

The HTTP server must call these functions. Tests call them directly,
with a temporary directory, and do not start Docker.
"""

from __future__ import annotations

from pathlib import Path


def join(path: str | Path, name: str) -> int:
    """Append one person and return the ticket number."""

    # Validate the original name before touching the file.
    if "\n" in name or "\r" in name:
        raise ValueError("Name cannot contain a newline")

    clean_name = name.strip()

    if not clean_name or len(clean_name) > 40:
        raise ValueError("Name must contain 1 to 40 characters")

    queue_path = Path(path)
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    existing_text = (
        queue_path.read_text(encoding="utf-8")
        if queue_path.exists()
        else ""
    )

    current_names = existing_text.splitlines()

    with queue_path.open("a", encoding="utf-8", newline="\n") as file:
        if existing_text and not existing_text.endswith(("\n", "\r")):
            file.write("\n")

        file.write(clean_name + "\n")

    return len(current_names) + 1


def take(path: str | Path) -> str:
    """Remove and return the first name."""

    queue_path = Path(path)

    try:
        names = queue_path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        raise LookupError("Queue file does not exist") from None

    if not names or not names[0].strip():
        raise LookupError("Queue is empty")

    first_name = names[0]
    remaining_names = names[1:]

    queue_path.write_text(
        "".join(name + "\n" for name in remaining_names),
        encoding="utf-8",
    )

    return first_name
