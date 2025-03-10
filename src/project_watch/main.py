"""Project monitoring core functionality with file system watching."""

# Standard library imports
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime

# Third-party imports
from watchdog.events import FileSystemEventHandler

logger = logging.getLogger(__name__)


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
    except (subprocess.SubprocessError, ValueError, AttributeError) as e:
        logger.debug("Pylint error: %s", str(e))
        score = 0.0
    finally:
        return min(max(score, 0.0), 10.0)


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
    try:
        if json_match := re.search(r'{"\w+": \d+.*}', output):
            _update_results_from_json(json.loads(json_match.group(0)), result)
            return True
        return False
    except (json.JSONDecodeError, AttributeError):
        return False


def _update_results_from_json(json_data: dict, result: dict) -> None:
    """Update results dict with data from JSON."""
    result.update(
        {
            "passed": json_data.get("passed", 0),
            "failed": json_data.get("failed", 0),
            "skipped": json_data.get("skipped", 0),
            "warnings": json_data.get("warnings", 0),
            "time": json_data.get("duration", 0.0),
        }
    )


def _parse_pytest_patterns(normalized_output: str, result: dict) -> None:
    """Match pytest output patterns and update results."""
    patterns = (
        (
            r"(\d+) passed.*?(\d+) failed.*?(\d+) warnings.*?(\d+) skipped.*? in ([\d.]+)s",
            5,
        ),
        (r"(\d+) passed.*?(\d+) failed.*?(\d+) errors.*? in ([\d.]+)s", 4),
        (r"(\d+) passed.*?(\d+) skipped.*? in ([\d.]+)s", 3),
        (r"(\d+) failed.*? in ([\d.]+)s", 2),
    )

    for pattern, _ in patterns:
        if match := re.search(pattern, normalized_output):
            # Process matched groups directly
            result.update(
                {
                    key: int(match.group(i + 1))
                    for i, key in enumerate(["passed", "failed", "warnings", "skipped"])
                    if i < len(match.groups()) - 1  # Last group is always time
                }
            )
            result["time"] = float(match.group(len(match.groups())))
            result.setdefault("skipped", 0)
            break  # Stop after first match


def _parse_pytest_text(output: str, result: dict) -> bool:
    """Fallback text parsing of pytest output."""
    # Add more robust pattern matching for text output
    text_patterns = [
        (r"(\d+) passed", "passed"),
        (r"(\d+) failed", "failed"),
        (r"(\d+) warnings", "warnings"),
        (r"(\d+) skipped", "skipped")
    ]
    
    # Try to extract time first
    time_match = re.search(r" in ([\d.]+)s", output)
    if time_match:
        result["time"] = float(time_match.group(1))
    
    # Extract test counts from text patterns
    found = False
    for pattern, key in text_patterns:
        match = re.search(pattern, output)
        if match:
            result[key] = int(match.group(1))
            found = True

    # Fallback for basic passed count
    if not found and (passed_match := re.search(r"(\d+) passed", output)):
        result["passed"] = int(passed_match.group(1))
        found = True

    # Check for empty test results
    if "no tests ran" in output.lower():
        result["error"] = "No tests executed"

    return found


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

        if sys.platform == "win32" and _is_windows_reserved_name(
            real_path.resolve().lower()
        ):
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
        try:
            if _should_skip_file(path, counted):
                continue

            # Resolve symlinks and check Windows reserved names
            real_path = path.resolve()
            if _is_windows_reserved_name(real_path):
                continue

            # Skip already counted files (via symlinks)
            if real_path in counted:
                continue
            counted.add(real_path)

            if real_path.is_file() and real_path.suffix == ".py":
                total += _count_file_lines(real_path)
        except (OSError, UnicodeDecodeError):
            continue

    return total


def _process_code_path(path: pathlib.Path, counted: set) -> int:
    """Process a single path for line counting."""
    try:
        # Resolve symlinks before processing
        resolved_path = path.resolve(strict=True)

        # Skip directory symlinks but follow file symlinks
        if resolved_path.is_dir():
            return 0

        # Normalize case for Windows after resolving
        if sys.platform == "win32":
            resolved_path = pathlib.Path(str(resolved_path).lower())

        if _should_skip_file(resolved_path, counted):
            logger.debug("Skipping file: %s", resolved_path)
            return 0

        line_count = _count_file_lines(resolved_path)
        logger.debug("Counted %d lines in %s", line_count, resolved_path)
        return line_count

    except (PermissionError, FileNotFoundError):
        return 0
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Error counting %s: %s", path, e, exc_info=True)
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
