from pathlib import PureWindowsPath

import pytest

from src.project_watch.main import (
    count_lines_of_code,
)  # pylint: disable=import-error,no-name-in-module


@pytest.mark.windows
def test_windows_path_handling(tmp_path):
    """Test handling of Windows-style paths and reserved names"""
    # Create test files
    d = tmp_path / "sub"
    d.mkdir()
    (d / "normal.py").write_text("# Valid Python file\nprint('hello')\n")
    (d / "con.py").write_text("# Reserved name\n")  # CON is reserved in Windows

    # Test path normalization with Windows-style paths
    win_path = PureWindowsPath(str(d))
    assert count_lines_of_code(win_path) == 2  # normal.py has 2 lines of code

    # Test reserved filename handling
    with pytest.raises(OSError):
        (d / "COM4.py").write_text("# Should fail in Windows")


@pytest.mark.windows
def test_windows_case_insensitivity(tmp_path):
    """Test case-insensitive file handling"""
    (tmp_path / "MiXeDcAsE.py").write_text("x = 1\nx = 2\n")
    assert count_lines_of_code(tmp_path) == 2


def test_windows_spaces_in_path(tmp_path):
    """Test paths with spaces"""
    dir_with_spaces = tmp_path / "dir with spaces"
    dir_with_spaces.mkdir()
    (dir_with_spaces / "file with spaces.py").write_text("print('test')\n")
    assert count_lines_of_code(dir_with_spaces) == 1


def test_windows_unc_paths(tmp_path):
    """Test UNC path handling"""
    # Create files using normal Path operations first
    share_path = tmp_path / "share"
    share_path.mkdir()
    test_file = share_path / "test.py"
    test_file.write_text("# UNC path test\nx = 1\n")

    # Then verify Windows path handling
    unc_path = PureWindowsPath(f"\\\\{tmp_path}\\share\\test.py")
    assert count_lines_of_code(unc_path.parent) == 2


def test_windows_mixed_slashes(tmp_path):
    """Test mixed forward/backward slashes"""
    # Create file with normal Path operations
    file_path = tmp_path / "mixed" / "slashes.py"
    file_path.parent.mkdir()
    file_path.write_text("a = 1\nb = 2\n")

    # Test Windows path representation
    mixed_path = PureWindowsPath(str(tmp_path) + "/mixed\\slashes.py")
    assert count_lines_of_code(mixed_path.parent) == 2
