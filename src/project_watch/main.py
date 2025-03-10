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
    
    # Improved score extraction with multiple fallbacks
    try:
        # First try regex pattern matching
        if match := re.search(r"rated at (\d+\.?\d*)/10", result.stdout):
            return float(match.group(1))
        
        # Fallback to splitting output
        parts = result.stdout.split()
        if "/10" in parts:
            return float(parts[parts.index("/10")-1])
            
    except (IndexError, ValueError, AttributeError):
        pass
    
    return 0.0  # Explicit default on failure


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
        passed = len(re.findall(r"^PASSED\b", result.stdout, flags=re.M))
        failed = len(re.findall(r"^FAILED\b", result.stdout, flags=re.M))

        output = result.stdout[-2000:]  # Truncate long output
        
        # Check for JSON parse errors
        if "INTERNALERROR" in output:
            return {"error": "pytest internal error", "output": output}
            
        return {
            "passed": passed,
            "failed": failed,
            "output": output,
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
            any(b"\0" in f.read(1024) for f in ([open(real_path, "rb")]  # Check binary last
                if path.is_file() else [""])  # Prevent opening directories
            ),
            # Windows reserved filename check
            (sys.platform == "win32" and path.name.split(".")[0].upper() in [
                "CON", "PRN", "AUX", "NUL", "COM1", "LPT1"]),
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
