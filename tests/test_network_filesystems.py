import contextlib
import errno
import time
import pathlib
import pytest
from project_watch.main import count_lines_of_code  # pylint: disable=no-name-in-module


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


class TrackedResolver:
    def __init__(self):
        self.resolve_times = []
        self.original_resolve = pathlib.Path.resolve
        
    def __call__(self, path):
        self.resolve_times.append(time.monotonic())
        if len(self.resolve_times) < 3:
            raise OSError(errno.ETIMEDOUT, "Simulated timeout")
        return self.original_resolve(path)

def test_network_retry_backoff(tmp_path, monkeypatch):
    """Validate exponential backoff timing between retries"""
    (tmp_path / "retry_test.py").write_text("# Retry test file\n")
    
    resolver = TrackedResolver()
    monkeypatch.setattr(pathlib.Path, "resolve", resolver)
    
    start_time = time.monotonic()
    count_lines_of_code(tmp_path)  # Trigger retries

    # Calculate delays from resolver's timestamps
    delays = [
        resolver.resolve_times[i+1] - resolver.resolve_times[i]
        for i in range(len(resolver.resolve_times)-1)
    ]
    
    # Verify retry count and delays
    assert len(resolver.resolve_times) == 3, "Expected 3 resolve attempts"
    assert 0.9 < delays[0] < 1.1, f"First delay ({delays[0]:.2f}s) out of range"
    assert 1.9 < delays[1] < 2.1, f"Second delay ({delays[1]:.2f}s) out of range"
    
    total_time = time.monotonic() - start_time
    assert 2.5 < total_time < 3.5, f"Total duration ({total_time:.2f}s) unexpected"


def test_mixed_network_errors(tmp_path, monkeypatch):
    """Test handling of different error types across retries"""
    (tmp_path / "mixed_errors.py").touch()

    error_sequence = iter([
        OSError(errno.ETIMEDOUT, "Timeout"),
        OSError(errno.EHOSTUNREACH, "Host unreachable"),
        PermissionError(errno.EACCES, "Permission denied"),
    ])

    def resolve_with_errors(self):
        try:
            raise next(error_sequence)
        except StopIteration:
            return pathlib.Path.resolve(self)
        return None  # Explicit fallback return

    monkeypatch.setattr(pathlib.Path, "resolve", resolve_with_errors)

    with pytest.raises(OSError) as exc_info:
        count_lines_of_code(tmp_path)

    assert exc_info.value.errno == errno.EACCES


def _create_delayed_resolve(original):
    """Create resolve function with simulated timeout errors"""

    def delayed_resolve(self, *args, **kwargs):
        for attempt in range(3):
            if attempt == 2:
                return original(self, *args, **kwargs)
            try:
                raise OSError(errno.ETIMEDOUT, "Simulated network timeout")
            except OSError as e:
                if attempt == 1:
                    raise OSError(errno.EHOSTUNREACH, "Final timeout") from e
                time.sleep(0.5 * (attempt + 1))
        raise OSError("Maximum retries exceeded")


    return delayed_resolve


@contextlib.contextmanager
def _timeout_context():
    """Context manager for timeout measurement"""
    start = time.monotonic()
    yield
    duration = time.monotonic() - start
    assert duration < 3, "Timeout handling failed"
