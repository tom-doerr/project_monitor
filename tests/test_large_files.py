import pathlib

# pylint: disable=wrong-import-order
import pytest  # pylint: disable=unused-import
from project_watch.main import count_lines_of_code  # pylint: disable=no-name-in-module


def generate_large_file(
    path: pathlib.Path, line_count: int, line_length: int = 1000
):  # pylint: disable=too-many-arguments
    # Generate all lines at once for better I/O performance
    data = ("a" * line_length + "\n") * line_count
    with path.open("w", encoding="utf-8") as f:
        f.write(data)


def test_10m_line_file(tmp_path: pathlib.Path):
    test_file = tmp_path / "large.txt"
    generate_large_file(test_file, 10_000_000)
    assert count_lines_of_code(tmp_path) == 10_000_000


def test_1gb_file(tmp_path: pathlib.Path):
    test_file = tmp_path / "huge.bin"
    # Write in single large chunk for better performance
    with test_file.open("wb") as f:
        f.write(b"\0" * (1024**3))  # 1GB file
        f.flush()  # Ensure all data is written before continuing
    assert count_lines_of_code(tmp_path) == 0


def test_safety_limits(tmp_path: pathlib.Path):
    test_file = tmp_path / "malformed.txt"
    with test_file.open("w", encoding="utf-8") as f:
        f.write("partial line")
    assert count_lines_of_code(tmp_path) == 0
