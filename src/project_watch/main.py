import subprocess
import pathlib
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


def get_pylint_score() -> float:
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
    result = subprocess.run(
        ["pytest", "--tb=no", "."], capture_output=True, text=True, check=False
    )
    return {
        "passed": result.returncode == 0,
        "summary": "\n".join(result.stdout.splitlines()[-3:-1]),
    }


def count_lines_of_code() -> int:
    total = 0
    for path in pathlib.Path(".").rglob("*.py"):
        with path.open() as f:
            total += sum(1 for _ in f)
    return total


class ProjectWatcher(FileSystemEventHandler):
    def __init__(self, update_callback):
        self.update_callback = update_callback

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".py"):
            self.update_callback()


def get_project_stats() -> dict:
    return {
        "pylint": get_pylint_score(),
        "pytest": get_pytest_results(),
        "loc": count_lines_of_code(),
        "last_updated": datetime.datetime.now(),
    }
