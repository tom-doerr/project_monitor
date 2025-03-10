import time
import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from project_watch.main import count_lines_of_code

def test_network_filesystem_latency(tmp_path):
    """Test handling of delayed network filesystem responses"""
    test_file = tmp_path / "delayed.py"
    test_file.write_text("# Valid Python file\nprint('hello')\n")
    
    # Simulate 500ms latency for path operations
    with patch("pathlib.Path.glob") as mock_glob:
        mock_glob.side_effect = lambda *args, **kwargs: [test_file]
        
        # First call - normal timing
        start = time.monotonic()
        assert count_lines_of_code(tmp_path) == 2
        normal_duration = time.monotonic() - start
        
        # Second call - simulated latency
        mock_glob.side_effect = lambda *args, **kwargs: (time.sleep(0.5) or [test_file]
        start = time.monotonic()
        assert count_lines_of_code(tmp_path) == 2
        delayed_duration = time.monotonic() - start
        
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
        [test_file]
    ]
    
    with patch("pathlib.Path.glob", mock_glob):
        assert count_lines_of_code(tmp_path) == 2
