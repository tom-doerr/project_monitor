"""Project monitoring core functionality with file system watching."""

import subprocess
import pathlib
import re
import sys
from datetime import datetime
from watchdog.events import FileSystemEventHandler  # Import kept for type hints


def get_pylint_score() -> float:
    """Calculate pylint score with robust parsing."""
    try:
        result = subprocess.run(
            ["pylint", "--disable=all", "--enable=similarities", "--score=yes", "src"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
            cwd=pathlib.Path(__file__).parent.parent,
        )

        # Directly target the score pattern with capture group
        match = re.search(r"rated at (\d+\.?\d*)/10", result.stdout)
        if match:
            return float(match.group(1))

        # Fallback for different output formats
        match = re.search(r"([\d\.]+)/10", result.stdout)
        return float(match.group(1)) if match else 0.0
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

    # Try to get precise numbers from summary line
    summary_match = re.search(
        r"(\d+) passed.*?(\d+) failed.*?(\d+) warnings.*?(\d+) skipped", 
        output.replace("\n", " ")
    )
    if summary_match:
        result["passed"] = int(summary_match.group(1))
        result["failed"] = int(summary_match.group(2))
        result["warnings"] = int(summary_match.group(3))
        result["skipped"] = int(summary_match.group(4))
    else:  # Fallback for older pytest versions
        result["passed"] = len(re.findall(r"PASSED", output))
        result["failed"] = len(re.findall(r"FAILED", output))
        result["warnings"] = len(re.findall(r"WARNING", output))
        result["skipped"] = len(re.findall(r"SKIPPED", output))

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
        real_path = path.resolve()
    except OSError:
        return True

    windows_reserved = sys.platform == "win32" and path.stem.upper() in {
        "con",
        "prn",
        "aux",
        "nul",
        "com1",
        "lpt1",
    }

    return any(
        [
            not path.exists(),
            real_path in counted,
            path.suffix != ".py",
            not path.is_file() or real_path.is_dir(),
            (
                path.is_file()
                and any(b"\0" in chunk for chunk in _read_file_chunks(real_path))
            ),
            windows_reserved,
        ]
    )


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
        # Handle symlinks to directories
        if path.is_symlink() and path.is_dir():
            continue
            
        # Normalize Windows paths
        if sys.platform == "win32":
            path = pathlib.Path(str(path).lower())

        if _should_skip_file(path, counted):
            continue
            
        try:
            line_count = _count_file_lines(path)
            total += line_count
        except PermissionError:
            continue  # Already logged in _should_skip_file
        except Exception as e:
            logging.warning(f"Error counting {path}: {e}", exc_info=True)

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
