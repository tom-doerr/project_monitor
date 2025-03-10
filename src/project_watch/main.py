"""Project monitoring core functionality with file system watching."""

import json
import logging
import subprocess
import pathlib
import re
import sys
from datetime import datetime
from watchdog.events import FileSystemEventHandler  # Import kept for type hints


def get_pylint_score() -> float:
    """Calculate pylint score with robust parsing."""

    def extract_score(text: str) -> float:
        """Extract score from pylint output text."""
        match = re.search(r"rated at (\d+\.?\d*)/10", text)
        return float(match.group(1)) if match else 0.0

    try:
        result = subprocess.run(
            ["pylint", "--disable=all", "--enable=similarities", "--score=yes", "src"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            cwd=pathlib.Path(__file__).parent.parent,
        )

        if result.returncode not in range(0, 32):  # Valid pylint exit codes
            return 0.0

        return max(extract_score(result.stdout), extract_score(result.stderr))
    except (subprocess.SubprocessError, ValueError, AttributeError):
        return 0.0


def _parse_pytest_output(output: str) -> dict:
    """Parse pytest output into structured results."""
    result = {
        "passed": 0,
        "failed": 0,
        "time": 0.0,
        "output": output[-2000:],
        "error": None,
    }

    if not _parse_pytest_json(output, result):
        _parse_pytest_text(output, result)

    return result


def _parse_pytest_json(output: str, result: dict) -> bool:
    """Attempt JSON parsing of pytest output, return True if successful."""
    json_match = re.search(r'{"\w+": \d+.*}', output)
    if not json_match:
        return False

    try:
        json_data = json.loads(json_match.group(0))
        result.update(
            {
                "passed": json_data.get("passed", 0),
                "failed": json_data.get("failed", 0),
                "skipped": json_data.get("skipped", 0),
                "warnings": json_data.get("warnings", 0),
                "time": json_data.get("duration", 0.0),
            }
        )
        return True
    except json.JSONDecodeError:  # pylint: disable=no-member
        return False
    summary_match = re.search(
        r"(\d+) passed.*?(\d+) failed.*?(\d+) warnings.*?(\d+) skipped.*? in ([\d.]+)s",
        output.replace("\n", " "),
    )
    if summary_match:
        result.update(
            {
                "passed": int(summary_match.group(1)),
                "failed": int(summary_match.group(2)),
                "warnings": int(summary_match.group(3)),
                "skipped": int(summary_match.group(4)),
                "time": float(summary_match.group(5)),
            }
        )

    # Try to get duration from output
    time_match = re.search(r" in ([\d.]+)s", output)
    if time_match:
        result["time"] = float(time_match.group(1))

    # Check for empty test results
    if "no tests ran" in output:
        result["error"] = "No tests executed"

    return result


def get_pytest_results() -> dict:
    """Run pytest and return results summary with error handling."""
    try:
        result = subprocess.run(
            ["pytest", "--tb=no", "."],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return _parse_pytest_output(result.stdout)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        error_msg = (
            "pytest timed out after 30 seconds"
            if isinstance(e, subprocess.TimeoutExpired)
            else f"Subprocess error: {str(e)}"
        )
        return {"error": error_msg}


def _should_skip_file(path: pathlib.Path, counted: set) -> bool:
    """Check if a file should be skipped during line counting."""
    try:
        real_path = path.resolve().absolute()

        if sys.platform == "win32":
            real_path = real_path.resolve().lower()
            if _is_windows_reserved_name(real_path):
                return True

        return any(
            (
                real_path in counted,
                real_path.suffix != ".py",
                not real_path.is_file(),
                any(b"\0" in chunk for chunk in _read_file_chunks(real_path)),
            )
        )

    except OSError:
        return True


def _is_windows_reserved_name(real_path: pathlib.Path) -> bool:
    """Check if path contains Windows reserved filename."""
    if sys.platform != "win32":
        return False

    stem = real_path.stem.split(".")[0].lower()
    reserved_names = (
        {"con", "prn", "aux", "nul"}
        | {f"com{i}" for i in range(1, 10)}
        | {f"lpt{i}" for i in range(1, 10)}
    )
    return stem in reserved_names


def _read_file_chunks(path: pathlib.Path, chunk_size: int = 1024) -> bytes:
    """Read file in chunks using context manager."""
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


def _count_file_lines(path: pathlib.Path) -> int:
    """Count non-empty lines in a file."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(
                1
                for line in f
                if line.strip()
                and len(line) <= 1000000
                and f.tell() < 10000000  # 10MB total read check
            )
    except (UnicodeDecodeError, PermissionError, FileNotFoundError, OSError) as e:
        is_permission_error = isinstance(e, PermissionError)
        if is_permission_error:
            print(f"Permission error reading {path}: {str(e)}")
        return 0


def count_lines_of_code(directory: str | pathlib.Path = pathlib.Path(".")) -> int:
    """Count total lines of Python code in the given directory."""
    total = 0
    counted = set()
    base_path = pathlib.Path(directory).resolve()

    for path in base_path.rglob("*"):
        total += _process_code_path(path, counted)

    return total


def _process_code_path(path: pathlib.Path, counted: set) -> int:
    """Process a single path for line counting."""
    if path.is_symlink() and path.is_dir():
        return 0

    normalized_path = (
        pathlib.Path(str(path).lower()) if sys.platform == "win32" else path
    )

    if _should_skip_file(normalized_path, counted):
        return 0

    try:
        return _count_file_lines(normalized_path)
    except PermissionError:
        return 0
    except (OSError, UnicodeDecodeError) as e:
        logger = logging.getLogger(__name__)
        logger.warning("Error counting %s: %s", normalized_path, e, exc_info=True)
        return 0


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
