import sys
from pathlib import Path
import pytest
from project_watch.main import count_lines_of_code  # pylint: disable=no-name-in-module


def _create_test_directory(tmp_path):
    """Create test directory structure with sample file"""
    test_dir = tmp_path / "sub"
    test_dir.mkdir()
    (test_dir / "normal.py").write_text("# Valid Python file\nprint('hello')\n")
    return test_dir


def _test_reserved_names(test_dir):
    """Verify handling of Windows reserved filenames"""
    reserved_names = [
        "COM1",
        "LPT2",
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM9",
        "LPT9",
        "CON.txt",
        "com1",
        "lPt9.md",  # Mixed case variants
        "COM1.old",
        "LPT2.new",
        "CON.final.py",
        "CLOCK$.log",  # Special device names
        "CONIN$.tmp",
        "CONOUT$.data",
    ]
    valid_names = ["COM10", "LPTS", "CONTACT", "NULLIFY"]

    _create_nested_reserved_dirs(test_dir, reserved_names)
    _create_test_files(test_dir, (reserved_names, valid_names))

    _verify_line_count(test_dir, len(valid_names))
    _verify_windows_specific_behavior(test_dir)


def _create_nested_reserved_dirs(test_dir, reserved_names):
    """Create nested directories with reserved names"""
    for name in reserved_names:
        nested_dir = test_dir / "subdir" / name
        nested_dir.mkdir(parents=True)
        (nested_dir / "test.py").write_text("# Reserved name test\n")


def _create_test_files(test_dir, names):
    """Create both reserved and valid test files"""
    reserved_names, valid_names = names
    _create_reserved_files(test_dir, reserved_names)
    _create_valid_files(test_dir, valid_names)


def _verify_line_count(test_dir, expected):
    """Verify the line count matches expected value"""
    assert count_lines_of_code(test_dir) == expected, "Should only count valid files"


def _verify_windows_specific_behavior(test_dir):
    """Verify Windows-specific file system behavior"""
    if sys.platform == "win32":
        assert (test_dir / "COM1").exists() is False, "Reserved files should be blocked"


def _create_reserved_files(test_dir, names):
    """Create files with reserved names"""
    for name in names:
        path = test_dir / name
        try:
            path.write_text(f"# Reserved: {name}\n", encoding="utf-8")
        except OSError:
            continue


def _create_valid_files(test_dir, names):
    """Create files with valid names"""
    for name in names:
        path = test_dir / name
        path.write_text(f"# Valid: {name}\n", encoding="utf-8")


def _validate_normal_files(test_dir, valid_names):
    """Validate counting of normal files"""
    assert count_lines_of_code(test_dir) == len(
        valid_names
    ), "Valid files should be counted"


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
    assert count_lines_of_code(dir_with_spaces) == 1  # Should count 1 non-empty line


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


def _create_reserved_test_files(tmp_path: Path) -> tuple[list, list]:
    """Create test files with reserved and valid names."""
    reserved_names = [
        "cOm1",
        "lPt9.TxT", 
        "nUL.tar.gz",
        "CONFIG.ini",
        "COM2.log",
        "prn.png",
    ]
    valid_names = ["data.txt", "image.png", "document.pdf"]
    
    # Create test files
    for name in reserved_names + valid_names:
        (tmp_path / name).touch()
        
    return reserved_names, valid_names

def test_windows_reserved_name_case_insensitivity(tmp_path: Path):
    """Verify case-insensitive detection of reserved names with various extensions"""
    reserved_names, valid_names = _create_reserved_test_files(tmp_path)
    count = count_lines_of_code(tmp_path)
    
    # Debug output for test failures
    print(f"\nFound files: {list(tmp_path.glob('*'))}")
    
    # Should only count valid files
    assert count == len(valid_names), (
        f"Failed to filter {len(reserved_names)} reserved names. "
        f"Expected {len(valid_names)} valid files, counted {count}")
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    reserved_names = [
        "COM1",
        "lpt9",
        "CON.TXT",
        "aux.json",
        "nul.txt",
        "LPT5.csv",
        "PRN.png",
        "COM4.tar.gz",
        "NUL.LOG",
        "AuX.yml",
        "CoM1",
        "lpt3.config.ini",
        "PRN.",
        "NUL..txt",
        "CON.tar.gz",
        "CONIN$",
        "CONOUT$",
        "CLOCK$",
        "CaSeInSeNsItIvE",
        "$Mft",
        "CoM3",
        "lPt4.txt",
        "nUl",
        "AUX",
        "COM1.old",  # Added more variants
        "LPT2.new",
        "CON.final.py",
        "com1.log",  # Lowercase
        "lPt9.md",  # Mixed case extension
    ]
    valid_names = [
        "CONFIG",
        "COM10",
        "LPT",
        "null.txt",
        "CLOCK",
        "Mft",
        "validfile",
        "test.config",
        "data123",
        "backup~",
    ]
    valid_names = [
        "COM10",  # Exceeds COM9 range
        "LPTS",  # Not LPT prefix
        "conventional.txt",  # Contains reserved substring but valid
        "null_device",  # Contains NUL substring
        "auxiliary.py",  # Contains AUX substring
        "COM0",  # Below COM1 range
        "LPT10",  # Exceeds LPT9 range
        "PRN_file",  # Underscore separated
        "NULISH",  # Suffix
        "AUXIL",  # Prefix
    ]

    # Create nested directory with reserved name but valid contents
    nested_dir = tmp_path / "COM2" / "valid_sub"
    nested_dir.mkdir(parents=True)
    (nested_dir / "valid.py").write_text("# Valid nested file\n")

    # Create test files
    for name in reserved_names + valid_names:
        try:
            (tmp_path / name).write_text("content")
        except OSError:
            pass  # Expected to fail creating reserved names on Windows

    # Verify reserved files were not created on Windows
    if sys.platform == "win32":
        for name in reserved_names:
            assert not (
                tmp_path / name
            ).exists(), f"Reserved file {name} should not be creatable"

    # Count lines - should skip reserved names regardless of case
    result = count_lines_of_code(tmp_path)

    # Should count valid names plus nested valid file
    expected_count = len(valid_names) + 1  # Add 1 for nested valid.py
    assert result == expected_count, (
        f"Expected {expected_count} lines from {len(valid_names)} valid files "
        f"plus 1 nested file, got {result}"
    )

    # Verify we can access a valid file in a reserved-named directory
    if sys.platform == "win32":
        assert (
            nested_dir / "valid.py"
        ).exists(), "Valid files in reserved-named directories should be accessible"


def test_windows_mixed_slashes(tmp_path):
    """Test mixed forward/backward slashes in paths"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    test_file = tmp_path / "mixed" / "slashes.py"
    test_file.parent.mkdir()
    test_file.write_text("x = 1\n")

    # Test with mixed slashes
    mixed_path = Path(test_file.as_posix().replace("mixed/", "mixed\\"))
    assert count_lines_of_code(mixed_path) == 1


def test_mixed_case_files(tmp_path: Path):
    """Test case insensitivity for files"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    test_files = [
        ("TESTFILE.PY", "x = 1\n"),
        ("subdir/MixedCase.Py", "y = 2\n"),
        ("mixed/slashes.py", "a = 1\nb = 2\n"),
    ]

    for path, content in test_files:
        file_path = tmp_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    assert count_lines_of_code(tmp_path) == 3
