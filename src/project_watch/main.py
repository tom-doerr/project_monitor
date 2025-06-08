"""Project monitoring core functionality with file system watching."""

# pylint: disable=too-many-lines

# Standard library imports
import errno
import json
import logging
import pathlib
import re
import subprocess
import sys
import time
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
        pattern = r"(?:rated at |score: )(\d+\.?\d*)/10"
        matches = re.findall(pattern, text, re.IGNORECASE)
        valid_scores = [float(m) for m in matches if 0.0 <= float(m) <= 10.0]
        return max(valid_scores) if valid_scores else 0.0

    def run_pylint():
        return subprocess.run(
            ("pylint", "--disable=all", "--enable=similarities", "--score=yes", "src"),
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            cwd=pathlib.Path(__file__).parent.parent,
        )

    try:
        proc = run_pylint()
        if getattr(proc, "returncode", 127) <= 31:
            return max(extract_score(proc.stdout), extract_score(proc.stderr))
        return 0.0
    except subprocess.TimeoutExpired as e:
        logger.warning("Pylint timed out after %s seconds", e.timeout)
        return 0.0
    except Exception as e:  # pylint: disable=broad-except
        logger.debug("Pylint error: %s", str(e), exc_info=True)
        return 0.0


def _parse_pytest_output(stdout: str, stderr: str = "", returncode: int = 0) -> dict:
    """Parse pytest output into structured results."""
    result = {
        "passed": 0,
        "failed": 0,
        "time": 0.0,
        "output": stdout,  # Use stdout as the output
        "error": "",  # Initialize as empty string
    }

    json_success = _parse_pytest_json(stdout, result)
    text_success = False
    if not json_success:
        text_success = _parse_pytest_text(stdout, result)
        # If text parsing succeeded, then clear any JSON error
        if text_success:
            result['error'] = ''

    # If both parsers failed and the return code is non-zero, set the error from stderr
    if not json_success and not text_success and returncode != 0:
        # Truncate long stderr
        stderr_msg = stderr.strip()
        if len(stderr_msg) > 500:
            stderr_msg = stderr_msg[:500] + "..."
        result['error'] = f"Pytest exited with code {returncode} ({stderr_msg})"

    return result


def _parse_pytest_json(output: str, result: dict) -> bool:
    """Attempt JSON parsing of pytest output, return True if successful."""
    json_match = re.search(r"^{.*}", output, re.DOTALL)
    if not json_match:
        return False

    try:
        json_data = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        result["error"] = f"JSON error: {str(e)}"
        return False

    if not isinstance(json_data, dict) or "passed" not in json_data:
        result["error"] = "Invalid JSON structure"
        return False

    _update_results_from_json(json_data, result)
    return True


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
    """Fallback text parsing for pytest output. Returns True if any patterns matched."""
    pattern_map = {
        "failed": r"(\d+) failed",
        "passed": r"(\d+) passed",
        "warnings": r"(\d+) warnings",
        "errors": r"(\d+) errors",
        "skipped": r"(\d+) skipped",
    }

    matches = {key: re.search(pattern, output) for key, pattern in pattern_map.items()}
    found = any(matches.values())
    
    if found:
        result.update({key: int(match.group(1)) for key, match in matches.items() if match})
        # Extract time from text output
        result['time'] = _extract_pytest_time(output)
    
    return found


def _extract_pytest_time(output: str) -> float:
    """Extract test execution time from output."""
    # Handle multiple time formats: 0.12s, 1.23 seconds, 0.12
    time_match = re.search(
        r"(\d+\.\d+)\s?(?:s|seconds?)?\b", output, re.IGNORECASE
    )
    if not time_match:  # Look for time in summary line
        time_match = re.search(r"\bin\s+(\d+\.\d+)\s*(?:s|seconds?)?\b", output, re.IGNORECASE)
    return float(time_match.group(1)) if time_match else 0.0


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


def _handle_pytest_error(e: Exception) -> dict:
    """Handle pytest errors and format response."""
    error_details = []
    if hasattr(e, "stderr") and e.stderr.strip():
        error_details.append(e.stderr.strip())
    if hasattr(e, "stdout") and e.stdout.strip():
        error_details.append(e.stdout.strip())
    return {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "error": (
            f"Pytest error: {' | '.join(error_details)[:500]}"
            if error_details
            else str(e)
        ),
    }


def get_pytest_results() -> dict:
    """Run pytest and return results summary with error handling."""
    try:
        proc = subprocess.run(
            ["pytest", "--tb=no", "."],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return _parse_pytest_output(proc.stdout, proc.stderr, proc.returncode)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError) as e:
        return _handle_pytest_error(e)


def _should_skip_file(path: pathlib.Path, counted: set) -> bool:
    """Check if a file should be skipped during line counting."""
    try:
        real_path = path.resolve(strict=True)
        file_id = (real_path.stat().st_ino, real_path.stat().st_dev)

        return (file_id in counted) or any(
            [
                not real_path.exists(),
                real_path.suffix != ".py",
                not real_path.is_file(),
                is_windows_reserved_path(real_path),
                any(b"\0" in chunk for chunk in _read_file_chunks(real_path)),
            ]
        )
    except OSError:
        return True






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
    if sys.platform == "win32":
        base_path = pathlib.Path(str(base_path).lower())

    return sum(_process_file(path, counted) for path in base_path.rglob("*"))


def _process_file(path: pathlib.Path, counted: set) -> int:
    """Process individual files for line counting."""
    try:
        if _should_skip_file(path, counted):
            return 0
        return _count_file_lines(path)
    except (OSError, IOError, UnicodeDecodeError, PermissionError) as e:
        _log_file_error(e, path)
        return 0


def _process_code_path(
    path: pathlib.Path, counted: set, inode_cache: set
) -> int:  # pylint: disable=too-many-arguments
    """Process a single path for line counting."""
    try:
        resolved_path = _resolve_with_retry(path)
        return _count_valid_file_lines(resolved_path, counted, inode_cache)
    except (PermissionError, FileNotFoundError, OSError, UnicodeDecodeError) as e:
        _log_file_error(e, path)
        return 0


def _resolve_with_retry(  # pylint: disable=too-many-arguments
    path: pathlib.Path, retries: int = 3, delay: float = 1.5
) -> pathlib.Path:
    """Resolve path with retries for network filesystem timeouts."""
    for attempt in range(retries + 1):
        try:
            return path.resolve(strict=True)
        except OSError as e:
            if (
                e.errno not in (errno.ETIMEDOUT, errno.EHOSTUNREACH)
                or attempt == retries
            ):
                raise IOError(
                    f"Path resolution failed after {retries} retries: {path}"
                ) from e
            time.sleep(delay * (2**attempt))

    raise IOError(f"Path resolution failed after {retries} retries: {path}")


def _count_valid_file_lines(path: pathlib.Path) -> int:
    """Count lines in valid, accessible files."""
    try:
        resolved_path = _resolve_with_retry(path)
        if not resolved_path.is_file():
            return 0
        return _count_file_lines(resolved_path)
    except (OSError, IOError, UnicodeDecodeError) as e:
        _log_file_error(e, path)
        return 0


def _log_file_error(error: Exception, path: pathlib.Path) -> None:
    """Log file processing errors with path context."""
    normalized_path = _normalize_path_case(path)
    logger.debug("Error processing %s: %s", normalized_path, str(error), exc_info=True)
    logger.error("Failed to process %s: %s", normalized_path, error)


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
