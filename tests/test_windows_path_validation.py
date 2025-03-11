"""Windows-specific path validation tests"""

import sys
from pathlib import Path
import pytest
from project_watch.main import count_lines_of_code  # pylint: disable=no-name-in-module


def test_windows_special_device_names(tmp_path: Path):
    """Test special device name handling"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    device_names = ["CONIN$", "CONOUT$", "CLOCK$"]
    valid_names = ["CONFIG", "CLOCK"]

    # Create test files
    for name in device_names + valid_names:
        (tmp_path / name).touch()

    count = count_lines_of_code(tmp_path)
    assert count == len(
        valid_names
    ), f"Should only count {len(valid_names)} valid files"


def test_ntfs_system_files(tmp_path: Path):
    """Test NTFS system file patterns"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    system_files = ["$Mft", "$LogFile", "$Volume"]
    valid_files = ["Mft", "LogFile", "Volume"]

    # Create test files
    for name in system_files + valid_files:
        (tmp_path / name).touch()

    count = count_lines_of_code(tmp_path)
    assert count == len(valid_files), "Should skip NTFS system files"


def test_reserved_name_variants(tmp_path: Path):
    """Test reserved name case variations"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    reserved_variants = ["CoM1", "lPt3", "nUl", "AUX"]
    valid_names = ["COM10", "LPTS", "null", "auxiliary"]

    # Create test files
    for name in reserved_variants + valid_names:
        (tmp_path / name).touch()

    count = count_lines_of_code(tmp_path)
    assert count == len(valid_names), "Should handle case variations correctly"


def test_reserved_names_with_extensions(tmp_path: Path):
    """Test reserved names with multiple extensions"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    reserved_files = [
        "COM1.txt",
        "lpt2.tar.gz",
        "nul.config.ini",
        "CONFIG.INI",
        "aux.backup.bak",
        "cOm1.TxT",  # Mixed case
        "LPT4.config.yml",  # Numeric suffix
        "nul..config",  # Double extension
        "CLOCK$.log",  # Special device
        "CONFIG~.tmp",  # Temporary file pattern
    ]
    valid_files = [
        "COM10.log",
        "lpt10.zip",
        "nullfile.txt",
        "config.ini",
        "auxiliary.bak",
    ]

    # Create test files with expected counts
    for name in reserved_files + valid_files:
        (tmp_path / name).touch()

    count = count_lines_of_code(tmp_path)
    assert count == len(valid_files), (
        f"Expected {len(valid_files)} valid files, found {count}. "
        "Reserved names with extensions should be skipped"
    )
