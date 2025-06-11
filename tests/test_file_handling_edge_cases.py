import pathlib
from unittest.mock import mock_open  # pylint: disable=wrong-import-order
import pytest  # pylint: disable=unused-import
from project_watch.main import count_lines_of_code


def test_mixed_line_endings(tmp_path: pathlib.Path):
    test_file = tmp_path / "mixed.txt"
    content = b"Line1\nLine2\r\nLine3\rLine4"
    test_file.write_bytes(content)
    assert count_lines_of_code(tmp_path) == 4


def test_invalid_utf8(tmp_path: pathlib.Path):
    test_file = tmp_path / "invalid.txt"
    # Write invalid UTF-8 sequence
    test_file.write_bytes(b"\xff\xfe\xfd\xfc")
    assert count_lines_of_code(tmp_path) == 0


def test_latin1_encoding(tmp_path: pathlib.Path):
    test_file = tmp_path / "latin1.txt"
    content = "Café".encode("iso-8859-1")
    test_file.write_bytes(content)
    assert count_lines_of_code(tmp_path) == 1


def test_windows_encoding(tmp_path: pathlib.Path):
    test_file = tmp_path / "windows.txt"
    content = "€•–".encode("windows-1252")
    test_file.write_bytes(content)
    assert count_lines_of_code(tmp_path) == 1


def test_partial_read_failure(tmp_path: pathlib.Path, monkeypatch):
    """Test that file read errors are handled gracefully."""
    test_file = tmp_path / "partial.txt"
    test_file.write_text("Valid\nContent")

    def mock_read_bytes(*args, **kwargs):
        raise IOError("Simulated read failure")

    monkeypatch.setattr(pathlib.Path, "read_bytes", mock_read_bytes)

    # The current implementation treats unreadable files as binary, resulting in 0 lines.
    assert count_lines_of_code(tmp_path) == 0
