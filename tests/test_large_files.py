import pathlib

# pylint: disable=wrong-import-order
import pytest  # pylint: disable=unused-import
from project_watch.main import count_lines_of_code  # pylint: disable=no-name-in-module


def generate_large_file(
    path: pathlib.Path, line_count: int, line_length: int = 1000
):  # pylint: disable=too-many-arguments
    with path.open("w", encoding="utf-8") as f:
        for _ in range(line_count):
            f.write("a" * line_length + "\n")


def test_10m_line_file(tmp_path: pathlib.Path):
    test_file = tmp_path / "large.txt"
    generate_large_file(test_file, 10_000_000)
    assert count_lines_of_code(tmp_path) == 10_000_000


def test_1gb_file(tmp_path: pathlib.Path):
    test_file = tmp_path / "huge.bin"
    with test_file.open("wb") as f:
        f.write(b"\0" * (1024**3))  # 1GB file
    assert count_lines_of_code(tmp_path) == 0


def test_safety_limits(tmp_path: pathlib.Path):
    test_file = tmp_path / "malformed.txt"
    with test_file.open("w", encoding="utf-8") as f:
        f.write("partial line")
    assert count_lines_of_code(tmp_path) == 0
