"""Windows-specific path validation tests"""

import sys
from pathlib import Path
import pytest
from project_watch.main import count_lines_of_code  # pylint: disable=no-name-in-module


def test_windows_special_device_names(tmp_path: Path):
    """Test handling of special device names with numeric suffixes"""
    if sys.platform != "win32":
        pytest.skip("Windows-specific test")

    reserved_names = [
        "COM1", "com2.txt", "LPT3.config", 
        "CONIN$", "conout$.log", "CLOCK$.ini",
        "COM0", "LPT0"  # Edge case numeric suffixes
    ]
    valid_names = ["COM0file", "lpt10.data", "conventional.txt"]
    
    # Create test files
    created = []
    for name in reserved_names + valid_names:
        path = tmp_path / name
        try:
            path.touch()
            created.append(path)
        except OSError:
            pass  # Expected for reserved names
            
    count = count_lines_of_code(tmp_path)
    
    # Only valid files should be counted
    assert count == len(valid_names), \
        f"Should reject {len(reserved_names)} reserved names. " \
        f"Got {count} valid files, expected {len(valid_names)}"


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

    reserved_variants = [
        "CoM1",
        "lPt3",
        "nUl",
        "AUX",
        "COM0",
        "LPT0",
        "CLOCK$",
        "CONIN$",
        "CONOUT$",
    ]
    valid_names = ["COM10", "LPTS", "null", "auxiliary", "COM0valid", "LPT0file"]

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
        "COM0.log",  # COM0 edge case
        "lpt2.tar.gz",
        "lpt0.config",  # LPT0 edge case
        "nul.config.ini",
        "CONFIG.INI",
        "aux.backup.bak",
        "cOm1.TxT",  # Mixed case
        "LPT4.config.yml",  # Numeric suffix
        "nul..config",  # Double extension
        "CLOCK$.log",  # Special device
        "CONFIG$",  # Extended device name
        "FAX$.tmp",  # Fax device
        "CONFIG~.tmp",  # Temporary file pattern
        "CONIN$.txt",  # Special device with extension
        "LPT1.config.ini",  # Reserved name with multiple extensions
        "COM1.",  # Empty extension
        "LPT1..test",  # Double dot extension
        "nul.tar.gz",  # Multiple extensions
        "ＣＯＮＩＮ＄.txt",  # Fullwidth Unicode homoglyph
        "ＣＯＭ１.txt",  # Fullwidth COM1
        "COM1. .txt",  # Space in extension
        "LPT1..config",  # Double dot extension
        "NUL.config..",  # Trailing double dot
        "COMⅨ.txt",  # Roman numeral homoglyph
        "CLOCK％.log",  # Unicode percent homoglyph
    ]
    valid_files = [
        "COM10.log",
        "lpt10.zip",
        "nullfile.txt",
        "config.ini",
        "auxiliary.bak",
        "conint.txt",  # Similar but not reserved
        "lpt10.config.ini",  # Valid numeric suffix
        "clock.log",  # Non-special device name
    ]

    # Create test files with expected counts
    for name in reserved_files + valid_files:
        (tmp_path / name).touch()

    count = count_lines_of_code(tmp_path)
    assert count == len(valid_files), (
        f"Expected {len(valid_files)} valid files, found {count}. "
        "Reserved names with extensions should be skipped"
    )
