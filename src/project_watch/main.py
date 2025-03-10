"""Project monitoring core functionality with file system watching."""

import subprocess
import pathlib
import re
import sys
from datetime import datetime
from watchdog.events import FileSystemEventHandler  # Import kept for type hints


def get_pylint_score() -> float:
    """Calculate pylint score with robust parsing."""
    result = subprocess.run(
        ["pylint", "--disable=all", "--enable=similarities", "--score=yes", "."],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    # Extract score using combined pattern matching
    patterns = (
        r"rated at (\d+\.?\d*)/10",  # Primary pattern
        r"([\d\.]+)/10",  # Fallback pattern
        r"\s(\d+\.\d+)\s+\(.*\)",  # Alternative format
    )

    scores = (
        float(match.group(1))
        for pattern in patterns
        if (match := re.search(pattern, result.stdout))
        for _ in (None,)
        if match
    )
    # Final fallback to split-based extraction
    parts = result.stdout.replace(",", "").split()
    scores = [float(s) for s in parts if s.replace(".", "").isdigit()]
    return max(scores) if scores else 0.0


def _parse_pytest_output(output: str) -> dict:
    """Parse pytest output into structured results."""
    passed = len(re.findall(r"PASSED", output))
    failed = len(re.findall(r"FAILED", output))
    time_match = re.search(r" in ([\d.]+)s", output)
    return {
        "passed": passed,
        "failed": failed,
        "time": float(time_match.group(1)) if time_match else 0.0,
        "output": output[-2000:],
    }


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
        error_msg = "pytest timed out after 30 seconds" if isinstance(e, subprocess.TimeoutExpired) else f"Subprocess error: {str(e)}"
        return {"error": error_msg}


def _should_skip_file(path: pathlib.Path, counted: set, windows_reserved_names: set) -> bool:
    """Check if a file should be skipped during line counting."""
        """Check if a file should be skipped."""
        try:
            real_path = path.resolve()
        except OSError:
            return True

        # Combined skip conditions (order matters for performance)
        skip_conditions = [
            not path.exists(),  # Handle broken symlinks first
            real_path in counted,  # Check cache before other ops
            path.suffix != ".py",
            not path.is_file() or real_path.is_dir(),  # Combine file/dir checks
            # Add Windows reserved name check
            # Check for binary files using context manager
            (path.is_file() and any(b"\0" in chunk for chunk in _read_file_chunks(real_path))),
            # Windows reserved filename check
            (sys.platform == "win32" and path.stem.upper() in _windows_reserved_names),
        ]

        # Check all conditions with proper error handling
        return any(skip_conditions)

def _read_file_chunks(path: pathlib.Path, chunk_size: int = 1024) -> bytes:
    """Read file in chunks using context manager."""
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk

def _count_file_lines(path: pathlib.Path) -> int:
        """Count non-empty lines in a file."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for line in f if line.strip())
        except (UnicodeDecodeError, PermissionError, FileNotFoundError, OSError) as e:
            is_permission_error = isinstance(e, PermissionError)
            if is_permission_error:
                print(f"Permission error reading {path}: {str(e)}")
            return 0

    total = 0
    for path in directory.rglob("*"):
        real_path = path.resolve()
        if not should_skip_file(path):
            total += count_file_lines(real_path)
            counted.add(real_path)

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
