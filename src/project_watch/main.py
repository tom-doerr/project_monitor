"""Project monitoring core functionality with file system watching."""
import subprocess
import pathlib
import datetime
from watchdog.events import FileSystemEventHandler


def get_pylint_score() -> float:
    """Calculate pylint score for the current directory."""
    result = subprocess.run(
        ["pylint", "--disable=all", "--enable=similarities", "--score=yes", "."],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        return float(result.stdout.split()[-2].split("/")[0])
    except (IndexError, ValueError):
        return 0.0


def get_pytest_results() -> dict:
    """Run pytest and return results summary."""
    result = subprocess.run(
        ["pytest", "--tb=no", "."], capture_output=True, text=True, check=False
    )
    return {
        "passed": result.returncode == 0,
        "summary": "\n".join(result.stdout.splitlines()[-3:-1]),
    }


def count_lines_of_code() -> int:
    """Count total lines of Python code in the project."""
    total = 0
    for path in pathlib.Path(".").rglob("*.py"):
        with path.open() as f:
            total += sum(1 for _ in f)
    return total


class ProjectWatcher(FileSystemEventHandler):
    """Watch for file changes and trigger updates."""
    def __init__(self, update_callback) -> None:
        self.update_callback = update_callback

    def on_modified(self, event) -> None:
        """Handle file modification events."""
        if not event.is_directory and event.src_path.endswith(".py"):
            self.update_callback()


def get_project_stats() -> dict:
    """Collect and return all project statistics."""
    return {
        "pylint": get_pylint_score(),
        "pytest": get_pytest_results(),
        "loc": count_lines_of_code(),
        "last_updated": datetime.datetime.now(),
    }
