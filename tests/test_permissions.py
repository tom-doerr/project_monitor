from unittest.mock import patch

import pytest

from project_watch.main import count_lines_of_code


def test_read_only_file(tmp_path):
    test_file = tmp_path / "readonly.py"  # Must be .py to count
    test_file.write_text("# Valid file\nprint('hello')\n\n")
    test_file.chmod(0o444)  # Set read-only

    try:
        assert count_lines_of_code(tmp_path) == 3  # 3 non-empty lines
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


@patch("project_watch.main.os.access")
def test_filesystem_errors(mock_access):
    mock_access.side_effect = PermissionError("Mocked permission error")
    with pytest.raises(PermissionError):
        count_lines_of_code()
