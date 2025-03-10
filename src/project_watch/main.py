"""Project monitoring core functionality with file system watching."""

import subprocess
import pathlib
import re
import sys
import json
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
    return next(scores, max(scores) if scores else 0.0)

    # Final fallback to split-based extraction
    parts = result.stdout.replace(",", "").split()
    scores = [float(s) for s in parts if s.replace(".", "").isdigit()]
    return max(scores) if scores else 0.0


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

        # Parse test counts from output
        passed = (
            int(re.findall(r"(\d+) passed", result.stdout)[-1])
            if "passed" in result.stdout
            else 0
        )
        failed = (
            int(re.findall(r"(\d+) failed", result.stdout)[-1])
            if "failed" in result.stdout
            else 0
        )

        output = result.stdout[-2000:]  # Truncate long output

        # Check for JSON parse errors
        if "INTERNALERROR" in output:
            return {"error": "pytest internal error", "output": output}

        time_match = re.search(r' in ([\d.]+)s', result.stdout)
        return {
            "passed": passed,
            "failed": failed,
            "time": float(time_match.group(1)) if time_match else 0.0,
            "output": output,
            **({"error": "pytest internal error"} if "INTERNALERROR" in output else {})
        }
    except subprocess.TimeoutExpired:
        return {"error": "pytest timed out after 30 seconds"}
    except subprocess.SubprocessError as e:  # More specific exception
        return {"error": f"Subprocess error: {str(e)}"}


def count_lines_of_code(directory: str | pathlib.Path = pathlib.Path(".")) -> int:
    """Count total lines of Python code in the given directory."""
    directory = pathlib.Path(directory).resolve()
    counted = set()

    def should_skip_file(path: pathlib.Path) -> bool:
        """Check if a file should be skipped."""
        real_path = path.resolve()

        # Combined skip conditions (order matters for performance)
        skip_conditions = [
            not path.exists(),  # Handle broken symlinks first
            real_path in counted,  # Check cache before other ops
            path.suffix != ".py",
            not path.is_file() or real_path.is_dir(),  # Combine file/dir checks
            any(  # Check for binary files
                b"\0" in content
                for content in (
                    [open(real_path, "rb").read(1024)] if path.is_file() else [b""]
                )
            ),
            # Windows reserved filename check
            (
                sys.platform == "win32"
                and path.name.split(".")[0].upper()
                in ["CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]
            ),
        ]

        # Check all conditions with proper error handling
        try:
            return any(skip_conditions)
        except OSError:
            return True

    def count_file_lines(path: pathlib.Path) -> int:
        """Count non-empty lines in a file."""
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return sum(1 for line in f if line.strip())
        except (PermissionError, FileNotFoundError, OSError) as e:
            print(f"Skipping {path}: {e}")
            return 0

    total = 0
    for path in directory.rglob("*"):
        if should_skip_file(path):
            continue

        real_path = path.resolve()
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
