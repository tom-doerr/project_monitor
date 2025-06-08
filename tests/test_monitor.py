"""Unit tests for dev_monitor.monitor module."""
import time
import logging
import pytest
from unittest.mock import patch, MagicMock
from dev_monitor.monitor import DevMonitor

@pytest.fixture
def mock_subprocess_run():
    with patch("subprocess.run") as mock_run:
        mock_process = MagicMock()
        mock_process.stdout = "Test output\nLines\nOf\nText"
        mock_run.return_value = mock_process
        yield mock_run

def test_capture_command_success(mock_subprocess_run, caplog):
    """Test successful command execution."""
    caplog.set_level(logging.INFO)
    monitor = DevMonitor()
    result = monitor.capture_command("test command", max_lines=2)
    assert "Test output\nLines" in result
    mock_subprocess_run.assert_called_once()

def test_capture_command_error(mock_subprocess_run):
    """Test command execution error handling."""
    mock_subprocess_run.side_effect = OSError("Test error")
    monitor = DevMonitor()
    result = monitor.capture_command("failing command")
    assert "Error: Test error" in result

def test_get_section_output_active():
    """Test output generation for active section."""
    monitor = DevMonitor()
    monitor.active_sections = {"test"}
    # pylint: disable-next=protected-access
    output = monitor._get_section_output("test", "[HEADER]", "cmd")
    assert "[HEADER]" in output
    assert time.ctime() in output

def test_get_section_output_inactive():
    """Test no output for inactive section."""
    monitor = DevMonitor()
    monitor.active_sections = set()
    # pylint: disable-next=protected-access
    output = monitor._get_section_output("test", "[HEADER]", "cmd")
    assert output == ""

@patch("os.path.exists", return_value=True)
def test_docker_section_output(mock_exists):
    """Test docker section output with compose file."""
    monitor = DevMonitor()
    test_sections = {"docker"}
    # pylint: disable-next=protected-access
    output = monitor._build_output(test_sections)
    assert "[DOCKER LOGS]" in output
    mock_exists.assert_called_once()

@patch("os.path.exists", return_value=False)
def test_docker_section_skipped(mock_exists):
    """Test docker section skipped without compose file."""
    monitor = DevMonitor()
    test_sections = {"docker"}
    # pylint: disable-next=protected-access
    output = monitor._build_output(test_sections)
    assert "[DOCKER LOGS]" not in output
