import time
import pathlib
from unittest.mock import patch
from project_watch.main import count_lines_of_code


def test_network_timeout_handling(tmp_path, monkeypatch):
    """Test handling of network filesystem timeouts"""
    # Setup
    test_file = tmp_path / "delayed.py"
    test_file.write_text("# Valid Python file\nprint('hello')\n")

    # Mock setup
    original_resolve = pathlib.Path.resolve
    monkeypatch.setattr(
        pathlib.Path, "resolve", _create_delayed_resolve(original_resolve)
    )

    # Execution
    with _timeout_context():
        result = count_lines_of_code(tmp_path)

    # Assertions
    assert result == 2


def _create_delayed_resolve(original):
    """Create resolve function with simulated latency"""
    # Add retry logic for network filesystems
    def delayed_resolve(self, *args, **kwargs):
        for attempt in range(3):
            try:
                time.sleep(2.5)
                return original(self, *args, **kwargs)
            except FileNotFoundError:
                if attempt == 2:
                    raise
                time.sleep(0.5 * attempt)

    return delayed_resolve


import contextlib


@contextlib.contextmanager
def _timeout_context():
    """Context manager for timeout measurement"""
    start = time.monotonic()
    yield
    duration = time.monotonic() - start
    assert duration < 3, "Timeout handling failed"
