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

    # Test path normalization
    win_path = PureWindowsPath(str(d))
    assert count_lines_of_code(root=win_path) == 3  # Test WindowsPath handling

    # Test reserved filename handling
    with pytest.raises(OSError):
        (d / "COM4.py").write_text("# Should fail in Windows")


@pytest.mark.windows
def test_windows_case_insensitivity(tmp_path):
    """Test case-insensitive file handling"""
    (tmp_path / "MiXeDcAsE.py").write_text("x = 1\nx = 2\n")
    assert count_lines_of_code(root=tmp_path) == 2
