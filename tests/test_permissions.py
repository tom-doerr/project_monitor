from unittest.mock import patch

import pytest

from project_watch.main import count_lines_of_code


def test_read_only_file(tmp_path):
    test_file = tmp_path / "readonly.txt"
    test_file.write_text("Line 1\nLine 2")
    test_file.chmod(0o444)  # Set read-only

    # Should still be able to read but not modify
    assert count_lines_of_code() == 2
    test_file.chmod(0o644)  # Cleanup permissions


def test_no_read_permission(tmp_path):
    test_dir = tmp_path / "secured"
    test_dir.mkdir()
    test_dir.chmod(0o000)  # No permissions

    with pytest.raises(PermissionError):
        count_lines_of_code()

    test_dir.chmod(0o755)  # Cleanup permissions


@patch("project_watch.main.os.access")
def test_filesystem_errors(mock_access):
    mock_access.side_effect = PermissionError("Mocked permission error")
    with pytest.raises(PermissionError):
        count_lines_of_code()
