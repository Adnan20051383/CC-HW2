"""Queue stored as one name per line, protected by a cross-process file lock."""

from __future__ import annotations

from contextlib import contextmanager
import os
from pathlib import Path
import tempfile

try:
    import fcntl
except ImportError:
    fcntl = None


@contextmanager
def _queue_lock(queue_path: Path):
    """Acquire a persistent lock shared by all processes using this queue."""
    lock_path = queue_path.parent / "queue.lock"

    with lock_path.open("a+b") as lock_file:
        if fcntl is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

        elif os.name == "nt":
            import msvcrt

            lock_file.seek(0, os.SEEK_END)
            if lock_file.tell() == 0:
                lock_file.write(b"\0")
                lock_file.flush()

            lock_file.seek(0)
            msvcrt.locking(
                lock_file.fileno(),
                msvcrt.LK_LOCK,
                1,
            )

            try:
                yield
            finally:
                lock_file.seek(0)
                msvcrt.locking(
                    lock_file.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
        else:
            raise RuntimeError("No supported file-locking mechanism")


def join(path: str | Path, name: str) -> int:
    """Append one person and return the ticket number."""

    if "\n" in name or "\r" in name:
        raise ValueError("Name cannot contain a newline")

    clean_name = name.strip()

    if not clean_name or len(clean_name) > 40:
        raise ValueError("Name must contain 1 to 40 characters")

    queue_path = Path(path)
    queue_path.parent.mkdir(parents=True, exist_ok=True)

    with _queue_lock(queue_path):
        try:
            existing_text = queue_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            existing_text = ""

        current_names = existing_text.splitlines()

        with queue_path.open(
            "a",
            encoding="utf-8",
            newline="\n",
        ) as file:
            if existing_text and not existing_text.endswith(("\n", "\r")):
                file.write("\n")

            file.write(clean_name + "\n")

        return len(current_names) + 1


def take(path: str | Path) -> str:
    """Remove and return the first name using atomic file replacement."""

    queue_path = Path(path)

    if not queue_path.parent.exists():
        raise LookupError("Queue file does not exist")

    with _queue_lock(queue_path):
        try:
            names = queue_path.read_text(
                encoding="utf-8"
            ).splitlines()
        except FileNotFoundError:
            raise LookupError("Queue file does not exist") from None

        if not names or not names[0].strip():
            raise LookupError("Queue is empty")

        first_name = names[0]
        remaining_names = names[1:]

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=queue_path.parent,
                prefix=f".{queue_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:

                temporary_path = Path(temporary_file.name)

                for name in remaining_names:
                    temporary_file.write(name + "\n")

                temporary_file.flush()
                os.fsync(temporary_file.fileno())

            os.replace(temporary_path, queue_path)
            temporary_path = None

        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass

        return first_name