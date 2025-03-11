import logging
from unittest.mock import patch
import pytest
from project_watch.main import count_lines_of_code


def test_read_only_file(tmp_path):
    test_file = tmp_path / "readonly.py"  # Must be .py to count
    test_file.write_text("# Valid file\nprint('hello')\n\n")
    test_file.chmod(0o444)  # Set read-only

    try:
        assert count_lines_of_code(tmp_path) == 2  # 2 non-empty lines
    finally:
        test_file.chmod(0o644)  # Ensure cleanup even if test fails


def test_no_read_permission(tmp_path):
    test_dir = tmp_path / "secured"
    test_dir.mkdir()
    (test_dir / "test.py").write_text("print('test')")  # Add test file
    test_dir.chmod(0o000)  # No permissions

    try:
        # Should return 0 instead of raising error
        assert count_lines_of_code(test_dir) == 0
    finally:
        test_dir.chmod(0o755)  # Ensure cleanup even if test fails


@patch("project_watch.main.pathlib.Path.resolve")
def test_filesystem_errors(mock_resolve, caplog):
    mock_resolve.side_effect = PermissionError("Mocked permission error")
    with caplog.at_level(logging.DEBUG):
        with pytest.raises(PermissionError):
            count_lines_of_code()
        assert "Mocked permission error" in caplog.text
    with pytest.raises(PermissionError):
        count_lines_of_code()


# Error cases shared across tests
ERROR_CASES = [
    (PermissionError, "Access is denied"),
    (FileNotFoundError, "The system cannot find the path specified"),
    (OSError, "Invalid argument"),
    (PermissionError, "Permission denied"),
    (FileNotFoundError, "No such file or directory"),
    (PermissionError, "Mocked permission error"),
    (OSError, "Input/output error"),
    (UnicodeDecodeError, "UTF-8 decode error"),
    (OSError, "Too many open files"),
    (OSError, "No space left on device"),
    (IsADirectoryError, "Is a directory"),
    (NotADirectoryError, "Not a directory"),
]


from unittest.mock import MagicMock


def test_filesystem_error_simulation(tmp_path, monkeypatch, caplog):
    """Test filesystem error handling with different exception types."""

    for exc_type, msg in ERROR_CASES:
        # Create mock that raises specific error with proper chaining
        monkeypatch.setattr(
            "project_watch.main._count_file_lines",
            lambda *args, **kwargs: (_ for _ in ()).throw(exc_type(msg))
        )
        caplog.clear()

        # Attempt to count lines
        with caplog.at_level(logging.ERROR):
            result = count_lines_of_code(tmp_path)
            assert result == 0, f"Failed to handle {exc_type.__name__}"
            
            # Verify error message contains both our custom message and the path
            assert any(
                msg in record.message and str(tmp_path) in record.message
                for record in caplog.records
            ), f"Missing expected error message for {exc_type.__name__}"
