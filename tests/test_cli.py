"""Unit tests for dev_monitor.cli module."""
import argparse
from unittest.mock import patch, MagicMock
from dev_monitor.cli import main, parse_args, print_startup_message

def test_parse_args_defaults():
    """Test CLI argument parsing with defaults."""
    args = parse_args()
    assert args.log_dir == "logs"
    assert args.interval == 1
    assert args.sections == ["docker", "pytest", "pylint"]

def test_parse_args_custom():
    """Test CLI argument parsing with custom values."""
    test_args = ["--log-dir", "custom_logs", "--interval", "5", "--sections", "pytest"]
    with patch("sys.argv", ["cli.py"] + test_args):
        args = parse_args()
    assert args.log_dir == "custom_logs"
    assert args.interval == 5
    assert args.sections == ["pytest"]

def test_print_startup_message(capsys):
    """Test the printed startup message."""
    args = argparse.Namespace(
        log_dir="test_logs",
        interval=30,
        sections=["docker", "pytest"]
    )
    print_startup_message(args)
    captured = capsys.readouterr()
    assert "Monitoring: docker, pytest" in captured.out
    assert "Logs directory: test_logs" in captured.out
    assert "Update interval: 30s" in captured.out

@patch("dev_monitor.cli.DevMonitor")
@patch("builtins.print")
def test_main_keyboard_interrupt(mock_print, mock_monitor):
    """Test handling of KeyboardInterrupt in main loop."""
    mock_monitor_instance = MagicMock()
    mock_monitor.return_value = mock_monitor_instance
    mock_monitor_instance.run.side_effect = KeyboardInterrupt
    main()
    mock_print.assert_called_with("\nMonitoring stopped")
