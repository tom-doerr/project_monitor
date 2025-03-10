import time
from unittest.mock import patch, Mock
import pathlib
import time
from unittest.mock import patch, Mock
from project_watch.main import count_lines_of_code


def test_network_timeout_handling(tmp_path, monkeypatch):
    """Test handling of network filesystem timeouts"""
    test_file = tmp_path / "delayed.py"
    test_file.write_text("# Valid Python file\nprint('hello')\n")

    original_resolve = pathlib.Path.resolve
    
    def delayed_resolve(self, *args, **kwargs):
        time.sleep(2.5)  # Simulate network latency
        return original_resolve(self, *args, **kwargs)
        
    monkeypatch.setattr(pathlib.Path, "resolve", delayed_resolve)
    
    start_time = time.monotonic()
    result = count_lines_of_code(tmp_path)
    duration = time.monotonic() - start_time
    
    assert result == 2
    assert duration < 3  # Verify timeout handling works


