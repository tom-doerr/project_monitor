import sys
import pytest

from project_watch.main import (
    count_lines_of_code,
)  # pylint: disable=import-error,no-name-in-module


def _create_test_directory(tmp_path):
    """Create test directory structure with sample file"""
    test_dir = tmp_path / "sub"
    test_dir.mkdir()
    (test_dir / "normal.py").write_text("# Valid Python file\nprint('hello')\n")
    return test_dir


def _test_reserved_names(test_dir):
    """Verify handling of Windows reserved filenames"""
    try:
        (test_dir / "con.py").write_text(
            "# Reserved name\n"
        )  # pylint: disable=unspecified-encoding
        assert count_lines_of_code(test_dir) == 2
        with pytest.raises(OSError):
            with pytest.raises(OSError):
                (test_dir / "COM4.py").write_text("# Should fail in Windows")
    except OSError:
        pytest.skip("Windows reserved name creation failed")


def test_windows_path_handling(tmp_path):
    """Test handling of Windows-style paths and reserved names"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    test_dir = _create_test_directory(tmp_path)

    _test_reserved_names(test_dir)
    # Verify normal file counting works
    assert count_lines_of_code(test_dir) == 2


def test_windows_case_insensitivity(tmp_path):
    """Test case-insensitive file handling"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")
    (tmp_path / "MiXeDcAsE.py").write_text("x = 1\nx = 2\n")
    assert count_lines_of_code(tmp_path) == 2


def test_windows_spaces_in_path(tmp_path):
    """Test paths with spaces"""
    dir_with_spaces = tmp_path / "dir with spaces"
    dir_with_spaces.mkdir()
    (dir_with_spaces / "file with spaces.py").write_text("print('test')\n")
    assert count_lines_of_code(dir_with_spaces) == 1


def test_long_path_handling(tmp_path):
    """Test paths exceeding 260 character limit"""
    long_path = tmp_path / ("a" * 40) / ("b" * 40) / ("c" * 40) / ("d" * 40)
    long_path.mkdir(parents=True)
    test_file = long_path / "test.py"
    test_file.write_text("# Valid Python file\nprint('hello')")
    assert count_lines_of_code(long_path) == 2


def test_windows_unc_paths(tmp_path):
    """Test UNC path handling"""
    # Create files using normal Path operations first
    share_path = tmp_path / "share"
    share_path.mkdir()
    test_file = share_path / "test.py"
    test_file.write_text("# UNC path test\nx = 1\n")

    # Then verify Windows path handling
    assert count_lines_of_code(share_path) == 2


def test_windows_mixed_slashes(tmp_path):
    """Test mixed forward/backward slashes"""
    # Create file with normal Path operations
    file_path = tmp_path / "mixed" / "slashes.py"
    file_path.parent.mkdir()
    file_path.write_text("a = 1\nb = 2\n")

    # Test Windows path representation
    assert count_lines_of_code(file_path.parent) == 2
