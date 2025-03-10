import time
from unittest.mock import patch, Mock
from project_watch.main import count_lines_of_code


def test_normal_timing(tmp_path):
    """Test normal filesystem timing"""
    test_file = tmp_path / "normal.py"
    test_file.write_text("# Valid Python file\nprint('hello')\n")

    with patch("pathlib.Path.glob") as mock_glob:
        mock_glob.return_value = [test_file]
        start = time.monotonic()
        assert count_lines_of_code(tmp_path) == 2
        return time.monotonic() - start


def test_network_filesystem_latency(tmp_path):
    """Test handling of delayed network filesystem responses"""
    test_file = tmp_path / "delayed.py"
    test_file.write_text("# Valid Python file\nprint('hello')\n")

    with patch("pathlib.Path.glob") as mock_glob:
        # Get normal timing baseline
        normal_duration = test_normal_timing(tmp_path)

        # Simulate latency and measure
        mock_glob.side_effect = lambda *args, **kwargs: (time.sleep(0.5) or [test_file])
        start = time.monotonic()
        assert count_lines_of_code(tmp_path) == 2
        delayed_duration = time.monotonic() - start

        # Verify latency impact
        assert delayed_duration - normal_duration >= 0.5


def test_transient_network_errors(tmp_path):
    """Test handling of temporary network filesystem failures"""
    test_file = tmp_path / "transient.py"
    test_file.write_text("# Valid Python file\nprint('hello')\n")

    # Simulate 2 failures before success
    mock_glob = Mock()
    mock_glob.side_effect = [
        IOError("Network filesystem unavailable"),
        IOError("Connection reset by peer"),
        [test_file],
    ]

    with patch("pathlib.Path.glob", mock_glob):
        assert count_lines_of_code(tmp_path) == 2
