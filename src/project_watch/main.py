"""Project monitoring core functionality with file system watching."""

# pylint: disable=too-many-lines

# Standard library imports
import json
import logging
import pathlib
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime

# Third-party imports
from watchdog.events import FileSystemEventHandler

# Local imports
from .path_validation import is_windows_reserved_path

logger = logging.getLogger(__name__)


def get_pylint_score() -> float:
    """Calculate pylint score with robust parsing."""

    def extract_score(text: str) -> float:
        """Extract score from pylint output text."""
        if match := re.search(r"rated at (\d+\.?\d*)/10", text):
            return max(0.0, min(float(match.group(1)), 10.0))
        return 0.0

    try:
        proc = subprocess.run(
            ["pylint", "--disable=all", "--enable=similarities", "--score=yes", "src"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            cwd=pathlib.Path(__file__).parent.parent,
        )

        if getattr(proc, "returncode", 127) <= 31:  # Handle missing returncode
            return max(extract_score(proc.stdout), extract_score(proc.stderr))
    except Exception as e:  # pylint: disable=broad-except
        logger.debug("Pylint error: %s", str(e))

    # Consolidate returns to avoid too-many-returns
    final_score = 0.0
    if proc and proc.returncode <= 31:
        final_score = max(extract_score(proc.stdout), extract_score(proc.stderr))
    return final_score


def _parse_pytest_output(output: str) -> dict:
    """Parse pytest output into structured results."""
    result = {
        "passed": 0,
        "failed": 0,
        "time": 0.0,
        "output": output,
        "error": "",  # Initialize as empty string
    }

    if not _parse_pytest_json(output, result):
        _parse_pytest_text(output, result)

    return result


def _parse_pytest_json(output: str, result: dict) -> bool:
    """Attempt JSON parsing of pytest output, return True if successful."""
    success = False
    json_match = re.search(r'{"\w+": \d+.*}', output)

    if json_match:
        try:
            json_data = json.loads(json_match.group(0))
            if isinstance(json_data, dict) and "passed" in json_data:
                _update_results_from_json(json_data, result)
                success = True
        except (json.JSONDecodeError, AttributeError, ValueError) as e:
            result["error"] = f"JSON parsing failed: {str(e)}"

    return success


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
            r"^(?:=+ )?(\d+) failed(?:, | in |$)",
            r"^(?:=+ )?(\d+) passed(?:, | in |$)",
            r"(\d+) warnings?\)?$",
            r"(\d+) errors?\)?$",
            r"(\d+) skipped\)?$",
        ),
    )
    # Initialize required fields explicitly
    result.setdefault("passed", 0)
    result.setdefault("failed", 0)

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
    """Fallback text parsing for pytest output."""
    pattern_map = {
        "failed": r"(\d+) failed",
        "passed": r"(\d+) passed",
        "warnings": r"(\d+) warnings",
        "errors": r"(\d+) errors",
        "skipped": r"(\d+) skipped",
    }

    matches = {key: re.search(pattern, output) for key, pattern in pattern_map.items()}

    result.update({key: int(match.group(1)) for key, match in matches.items() if match})

    return any(matches.values())


def _extract_pytest_time(output: str) -> float:
    """Extract test execution time from output."""
    if match := re.search(r" in ([\d.]+)s", output):
        return float(match.group(1))
    return 0.0


@dataclass
class PatternMatchParams:
    pattern: str
    groups: int
    output: str
    result: dict


def _match_pattern(params: PatternMatchParams) -> bool:
    """Match a single output pattern and update results."""
    if not (match := re.search(params.pattern, params.output)):
        return False

    params.result["passed"] = int(match.group(1))
    if params.groups >= 2:
        params.result["failed"] = int(match.group(2))
    if params.groups >= 3:
        params.result["warnings"] = int(match.group(3)) if params.groups == 4 else 0
    if params.groups >= 4:
        params.result["skipped"] = int(match.group(4))
    return True


def _handle_empty_results(output: str, result: dict) -> bool:
    """Check for empty test results."""
    if "no tests ran" in output.lower() or "collected 0 items" in output.lower():
        result.update(
            {
                "error": "No tests executed",
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "warnings": 0,
            }
        )
        return True
    return False


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
        # Include both stderr and stdout in error details
        error_details = []
        if hasattr(e, "stderr") and e.stderr.strip():
            error_details.append(e.stderr.strip())
        if hasattr(e, "stdout") and e.stdout.strip():
            error_details.append(e.stdout.strip())

        error_msg = (
            f"Pytest error: {' | '.join(error_details)[:500]}"
            if error_details
            else str(e)
        )
        return {"passed": 0, "failed": 0, "skipped": 0, "error": error_msg}


def _should_skip_file(path: pathlib.Path, counted: set) -> bool:
    """Check if a file should be skipped during line counting.
    Valid skip reasons:
    - Already counted via inode tracking
    - Path doesn't exist
    - Not a Python file
    - Windows reserved path name
    - Contains null bytes
    """
    try:
        real_path = path.resolve()
        file_id = (real_path.stat().st_ino, real_path.stat().st_dev)
        return any(
            [
                file_id in counted,
                not real_path.exists(),
                real_path.suffix != ".py",
                not real_path.is_file(),
                _is_windows_reserved_path(real_path),
                any(b"\0" in chunk for chunk in _read_file_chunks(real_path)),
            ]
        )
    except OSError:
        return True


def _is_windows_reserved_path(path: pathlib.Path) -> bool:
    """Check if path contains Windows reserved names."""
    return is_windows_reserved_path(path)


def _is_windows_reserved_name(real_path: pathlib.Path) -> bool:
    """Check if path contains Windows reserved filename."""
    if sys.platform != "win32":
        return False

    # Case-insensitive match for reserved names with extensions and variants
    reserved_pattern = (
        r"^(CON|PRN|AUX|NUL|CLOCK\$|"
        r"COM[0-9]|LPT[0-9]|"  # Include COM0/LPT0
        r"\$Mft|\$LogFile|\$Volume|"
        r"CONIN\$|CONOUT\$|FAX\$|CONFIG\$)(\..*)?$"
    )
    reserved_pattern = re.compile(reserved_pattern, re.IGNORECASE)
    return reserved_pattern.fullmatch(real_path.name) is not None


def _read_file_chunks(path: pathlib.Path, chunk_size: int = 1024) -> bytes:
    """Read file in chunks using context manager."""
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


def _count_file_lines(path: pathlib.Path) -> int:
    """Count non-empty lines in a file."""
    try:
        with path.open(encoding="utf-8", errors="ignore") as f:
            return sum(
                1
                for line in f
                if line.strip() and len(line) <= 100000  # Match test case value
            )
    except (PermissionError, UnicodeDecodeError, FileNotFoundError, OSError) as e:
        logger.log(
            logging.WARNING if isinstance(e, PermissionError) else logging.DEBUG,
            "Error counting %s: %s",
            path,
            str(e),
        )
        return 0


def count_lines_of_code(directory: str | pathlib.Path = pathlib.Path(".")) -> int:
    """Count total lines of Python code in the given directory."""
    counted = set()
    base_path = pathlib.Path(directory).resolve().absolute()

    # Normalize Windows paths to lowercase
    base_path = (
        pathlib.Path(str(base_path).lower()) if sys.platform == "win32" else base_path
    )

    return sum(_process_file(path, counted) for path in base_path.rglob("*"))


def _process_file(path: pathlib.Path, counted: set) -> int:
    """Process individual files for line counting."""
    try:
        return (
            0
            if _should_skip_file(path, counted)
            else _count_valid_file_lines(path, counted)
        )
    except (OSError, IOError, UnicodeDecodeError, PermissionError) as e:
        _log_file_error(e, path)
        return 0


def _process_code_path(path: pathlib.Path, counted: set) -> int:
    """Process a single path for line counting."""
    try:
        return _count_valid_file_lines(path, counted)
    except (PermissionError, FileNotFoundError, OSError, UnicodeDecodeError) as e:
        _log_file_error(e, path)
        return 0


def _count_valid_file_lines(path: pathlib.Path, counted: set) -> int:
    """Count lines in valid, accessible files."""
    resolved_path = path.resolve(strict=True)
    normalized_path = _normalize_path_case(resolved_path)

    if _should_skip_file(normalized_path, counted) or not normalized_path.is_file():
        return 0

    line_count = _count_file_lines(normalized_path)
    logger.debug("Counted %d lines in %s", line_count, normalized_path)
    return line_count


def _log_file_error(error: Exception, path: pathlib.Path) -> None:
    """Log file processing errors with path context."""
    normalized_path = _normalize_path_case(path)
    logging.debug("Error processing %s: %s", normalized_path, str(error), exc_info=True)
    logging.error("Failed to process %s: %s", normalized_path, error)


def _normalize_path_case(path: pathlib.Path) -> pathlib.Path:
    """Normalize path case for Windows systems."""
    if sys.platform == "win32":
        return pathlib.Path(str(path).lower())
    return path


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
