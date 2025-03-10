"""Project monitoring core functionality with file system watching."""

import subprocess
import pathlib
import re
from datetime import datetime
from watchdog.events import FileSystemEventHandler  # Import kept for type hints


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


def get_pytest_results() -> dict:  # pylint: disable=too-many-return-statements
    """Run pytest and return results summary."""
    try:
        result = subprocess.run(
            ["pytest", "--tb=no", "."],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,  # Add timeout protection
        )
        # Parse test counts from output
        passed = len(re.findall(r"^PASSED\b", result.stdout, flags=re.M))
        failed = len(re.findall(r"^FAILED\b", result.stdout, flags=re.M))

        return {
            "passed": passed,
            "failed": failed,
            "output": result.stdout[-2000:],  # Truncate long output
        }
    except subprocess.TimeoutExpired:
        return {"error": "pytest timed out after 30 seconds"}
    except subprocess.SubprocessError as e:  # More specific exception
        return {"error": f"Subprocess error: {str(e)}"}


def count_lines_of_code() -> (
    int
):  # pylint: disable=too-many-statements,too-many-nested-blocks
    """Count total lines of Python code in the project."""
    total = 0
    for path in pathlib.Path(".").rglob("*"):
        # Reduce nesting by filtering first
        if not (path.suffix == ".py" and path.is_file()):
            continue
        try:
            with path.open(encoding="utf-8") as f:
                total += sum(1 for line in f if line.strip())
        except UnicodeDecodeError:
            # Skip binary files masquerading as Python files
            continue
        except OSError as e:
            print(f"Error reading {path}: {e}")
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
        "last_updated": datetime.now(),
    }
