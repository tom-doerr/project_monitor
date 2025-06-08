# pylint: disable=too-many-lines
import sys
from pathlib import Path
from unittest.mock import patch
import pytest
from project_watch.path_validation import is_windows_reserved_path
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


@pytest.mark.parametrize(
    "unc_name,path_suffix,expected_lines,expected_error",
    [
        # Valid cases
        ("share", "test.py", 2, None),
        ("valid_dir", "data.csv", 3, None),
        # Reserved name cases
        ("\\\\server\\CONIN$", None, None, "reserved Windows name"),
        ("\\\\Server\\ClOcK$", None, None, "reserved Windows name"),
        ("COM1", "valid.txt", 1, None),
        ("CoM2", "file.txt", 1, None),
        ("CLOCK$", "time.txt", 1, None),
        ("CONFIG$", "settings.ini", None, "reserved Windows name"),
        ("LPT9", "output.txt", None, "reserved Windows name"),
        # Edge cases
        ("very_long_directory_name" * 10, "long.txt", 1, None),
        ("mixED/case/Path", "file.txt", 1, None),
        ("con", None, None, "reserved Windows name"),  # CON is reserved
        ("aux.py", None, None, "reserved Windows name"),
        ("nul.tar.gz", None, None, "reserved Windows name"),
        ("COM0", "data.bin", None, "reserved Windows name"),  # COM0-COM9
        ("lpt1.log", None, None, "reserved Windows name"),
    ],
)
def test_windows_unc_paths(
    tmp_path, unc_name, path_suffix, expected_lines, expected_error
):  # pylint: disable=too-many-arguments,too-many-locals,too-many-statements
    """Test UNC path handling with various reserved names and cases."""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    test_dir = tmp_path / unc_name
    test_dir.mkdir(parents=True, exist_ok=True)

    # Create test file if specified and expected_lines is set
    if path_suffix and expected_lines is not None:
        test_file = test_dir / path_suffix
        test_file.write_text("# Test content\n" * expected_lines)

        # Verify file was actually created if no error expected
        if expected_error is None:
            assert test_file.exists(), f"Test file {test_file} was not created"

    # Validate expectations
    if expected_error:
        # Check if path validation catches the reserved name
        if is_windows_reserved_path(test_dir):
            with pytest.raises(ValueError, match=expected_error):
                count_lines_of_code(test_dir)
        else:
            pytest.fail(f"Expected reserved path error for {test_dir}")
        return

    result = count_lines_of_code(test_dir)
    assert (
        result == expected_lines
    ), f"Expected {expected_lines}, got {result} for {unc_name}"


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


@patch("platform.system", return_value="Windows")
def test_windows_special_devices(_mock_platform, tmp_path: Path):
    """Test special device name handling (CONIN$, CONOUT$, CLOCK$)"""
    _run_reserved_name_test(
        tmp_path,
        (
            ["CONIN$", "CONOUT$.log", "CLOCK$.tmp", "COM1.txt", "LPT2.test"],
            ["CONFIG", "clock", "CONIN", "com10", "lpt0"],
        ),
    )


@patch("platform.system", return_value="Windows")
def test_windows_numeric_suffixes(_mock_platform, tmp_path: Path):
    """Test COM/LPT numeric suffix handling"""
    _run_reserved_name_test(
        tmp_path,
        (["COM1", "LPT9", "COM0", "lPt3"], ["COM10", "LPTS", "COMX"]),
    )


@patch("platform.system", return_value="Windows")
def test_windows_case_variants(_mock_platform, tmp_path: Path):
    """Test mixed case reserved name variants"""
    _run_reserved_name_test(
        tmp_path,
        (["CoM1", "nUl", "AuX", "pRn"], ["Compass", "Nullify", "Auxiliary"]),
    )


@patch("platform.system", return_value="Windows")
def test_windows_system_files(_mock_platform, tmp_path: Path):
    """Test NTFS system file patterns"""
    _run_reserved_name_test(
        tmp_path,
        (["$Mft", "$LogFile", "$Volume"], ["Mft", "LogFile", "Volume"]),
    )


def _run_reserved_name_test(
    tmp_path: Path, test_cases: tuple[list, list]
):  # pylint: disable=too-many-locals,too-many-statements
    """Validate Windows reserved name handling.

    Args:
        tmp_path: Temporary directory path
        test_cases: Tuple of (reserved_names, valid_names) to test
    """
    reserved_names, valid_names = test_cases

    # Create test files and handle expected OSErrors
    for name in (*reserved_names, *valid_names):
        if name in reserved_names:
            _attempt_reserved_file(tmp_path / name)
        else:
            (tmp_path / name).write_text("content")

    # Verify line count matches valid files only (should exclude all reserved names)
    valid_count = count_lines_of_code(tmp_path)

    # Debug output for test failures
    print(f"Reserved names: {reserved_names}")  # noqa: T201
    print(f"Valid names: {valid_names}")  # noqa: T201
    print(f"Actual count: {valid_count}")  # noqa: T201

    assert valid_count == len(valid_names), (
        f"Expected {len(valid_names)} valid lines, got {valid_count}.\n"
        f"Reserved: {reserved_names}\nValid: {valid_names}\n"
        "Check if any reserved files were actually created"  # nosec
    )


def _attempt_reserved_file(path: Path) -> None:
    """Attempt to create reserved file, ignoring expected OSError"""
    try:
        path.write_text("content")
    except OSError:
        pass


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
