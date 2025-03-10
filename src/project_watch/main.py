"""Project monitoring core functionality with file system watching."""

# Standard library imports
import json
import logging
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

    score = 0.0
    try:
        result = subprocess.run(
            ["pylint", "--disable=all", "--enable=similarities", "--score=yes", "src"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            cwd=pathlib.Path(__file__).parent.parent,
        )

        # Check if returncode exists before comparison
        if hasattr(result, "returncode") and 0 <= result.returncode <= 31:
            score = max(extract_score(result.stdout), extract_score(result.stderr))
    except (subprocess.SubprocessError, ValueError, AttributeError) as e:
        logger.debug("Pylint error: %s", str(e))

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
        json_match = re.search(r'{"\w+": \d+.*}', output)
        if not json_match:
            return False
            
        _update_results_from_json(json.loads(json_match.group(0)), result)
        return True
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
    # Extract time first
    time_match = re.search(r" in ([\d.]+)s", output)
    if time_match:
        result["time"] = float(time_match.group(1))

    # Check for test counts using single pattern
    count_match = re.search(
        r"(\d+) passed.*?(\d+) failed.*?(\d+) warnings.*?(\d+) skipped",
        output.replace("\n", " "),
    )
    if count_match:
        result["passed"] = int(count_match.group(1))
        result["failed"] = int(count_match.group(2))
        result["warnings"] = int(count_match.group(3))
        result["skipped"] = int(count_match.group(4))
        return True

    # Fallback for basic passed count
    if passed_match := re.search(r"(\d+) passed", output):
        result["passed"] = int(passed_match.group(1))
        return True

    # Check for empty results
    if "no tests ran" in output.lower():
        result["error"] = "No tests executed"
        return True

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
        return {"passed": 0, "failed": 0, "skipped": 0, "error": error_msg}


def _should_skip_file(path: pathlib.Path, counted: set) -> bool:
    """Check if a file should be skipped during line counting."""
    try:
        real_path = path.resolve()
        if not real_path.exists():
            return True

        return any((
            real_path in counted,
            real_path.suffix != ".py",
            not real_path.is_file(),
            _is_windows_reserved_path(real_path),
            any(b"\0" in chunk for chunk in _read_file_chunks(real_path))
        ))
    except OSError:
        return True

def _is_windows_reserved_path(path: pathlib.Path) -> bool:
    """Check if path is a Windows reserved filename."""
    return sys.platform == "win32" and _is_windows_reserved_name(path.resolve().lower())


def _is_windows_reserved_name(real_path: pathlib.Path) -> bool:
    """Check if path contains Windows reserved filename."""
    if sys.platform != "win32":
        return False

    # Check base name without extensions or numeric suffixes
    stem = real_path.stem.split(".")[0].lower()
    reserved_names = {
        "con",
        "prn",
        "aux",
        "nul",
        *{f"com{i}" for i in range(1, 10)},
        *{f"lpt{i}" for i in range(1, 10)},
    }
    return stem in reserved_names


def _read_file_chunks(path: pathlib.Path, chunk_size: int = 1024) -> bytes:
    """Read file in chunks using context manager."""
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


def _count_file_lines(path: pathlib.Path) -> int:
    """Count non-empty lines in a file."""
    line_count = 0
    try:
        with path.open(encoding="utf-8", errors="ignore") as f:
            line_count = sum(1 for line in f if line.strip())
    except PermissionError as e:
        logger.warning("Permission denied reading %s: %s", path, str(e))
    except (UnicodeDecodeError, FileNotFoundError, OSError) as e:
        logger.debug("Error counting lines in %s: %s", path, str(e))
    return line_count


def count_lines_of_code(directory: str | pathlib.Path = pathlib.Path(".")) -> int:
    """Count total lines of Python code in the given directory."""
    total = 0
    counted = set()
    base_path = pathlib.Path(directory).resolve()

    def _process_path(path: pathlib.Path) -> None:
        """Process individual path and accumulate line count."""
        nonlocal total
        try:
            real_path = path.resolve()
            if _should_skip_file(path, counted) or real_path in counted:
                return
                
            counted.add(real_path)
            if real_path.is_file() and real_path.suffix == ".py":
                total += _count_file_lines(real_path)
        except (OSError, UnicodeDecodeError):
            return

    for path in base_path.rglob("*"):
        _process_path(path)

    return total


def _process_code_path(path: pathlib.Path, counted: set) -> int:
    """Process a single path for line counting."""
    line_count = 0
    try:
        resolved_path = path.resolve(strict=True)
        if resolved_path.is_dir():
            return 0

        if sys.platform == "win32":
            resolved_path = pathlib.Path(str(resolved_path).lower())

        if not _should_skip_file(resolved_path, counted):
            line_count = _count_file_lines(resolved_path)
            logger.debug("Counted %d lines in %s", line_count, resolved_path)
            
    except (PermissionError, FileNotFoundError, OSError, UnicodeDecodeError) as e:
        logger.warning("Error counting %s: %s", path, e, exc_info=True)
        
    return line_count


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
