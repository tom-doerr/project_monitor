import mimetypes
import re
import subprocess
from pathlib import Path


def _is_binary_by_content(path: Path) -> bool:
    """Check for null bytes in file content."""
    try:
        with path.open("rb") as f:
            return b"\x00" in f.read(4096)
    except IOError:
        return True  # Assume binary if unreadable


def is_binary(path: Path) -> bool:
    """Check if file is binary."""
    mime, _ = mimetypes.guess_type(str(path))
    if mime and not mime.startswith("text/"):
        return True
    return _is_binary_by_content(path)


def _read_lines(path: Path) -> int:
    """Read and count lines in a text file."""
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0


def _count_lines_in_file(path: Path, inode_cache: set) -> int:
    """Count lines of code in a single file, checking for duplicates and binary content."""
    lines = 0
    try:
        inode = path.stat().st_ino
        if inode not in inode_cache and not is_binary(path):
            inode_cache.add(inode)
            lines = _read_lines(path)
    except OSError:
        pass  # lines is already 0
    return lines


def count_lines_of_code(path: Path, inode_cache: set = None) -> int:
    """Recursively count lines of code in a directory, handling symlinks and binary files."""
    if inode_cache is None:
        inode_cache = set()

    lines = 0
    if path.exists():
        if path.is_dir():
            lines = sum(count_lines_of_code(child, inode_cache) for child in path.iterdir())
        else:
            lines = _count_lines_in_file(path, inode_cache)
    return lines


def get_pylint_score(directory_path: str) -> float:
    """Calculate pylint score for a directory."""
    try:
        result = subprocess.run(
            ["pylint", "--output-format=text", directory_path],
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout
        match = re.search(r"Your code has been rated at (\d+\.\d+)/10", output)
        return float(match.group(1)) if match else 0.0
    except (FileNotFoundError, ValueError) as err:
        print(f"Pylint error: {err}")
        return 0.0


def _parse_pytest_output(output: str) -> dict:
    """Parse pytest output to extract test results."""
    passed = re.search(r"(\d+) passed", output)
    failed = re.search(r"(\d+) failed", output)
    errors = re.search(r"(\d+) error", output)

    return {
        "passed": int(passed.group(1)) if passed else 0,
        "failed": int(failed.group(1)) if failed else 0,
        "errors": int(errors.group(1)) if errors else 0,
    }


def get_pytest_results(directory_path: str) -> dict:
    """Get pytest results for a directory."""
    try:
        result = subprocess.run(
            ["pytest", directory_path],
            capture_output=True,
            text=True,
            check=False,
        )
        return _parse_pytest_output(result.stdout)
    except (FileNotFoundError, ValueError) as err:
        print(f"Pytest error: {err}")
        return {"passed": 0, "failed": 0, "errors": 1}


def get_project_stats(directory_path: str) -> dict:
    """Get project statistics for a directory."""
    path = Path(directory_path)
    try:
        files = sum(1 for f in path.rglob("*") if f.is_file())
        lines = count_lines_of_code(path)
        # Complexity calculation can be added here later
        return {"files": files, "lines": lines, "complexity": 0.0}
    except OSError as err:
        print(f"Stats error: {err}")
        return {"files": 0, "lines": 0, "complexity": 0.0}
