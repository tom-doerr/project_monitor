import contextlib
import errno
import time
import pathlib
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


def test_network_retry_backoff(tmp_path, monkeypatch):
    """Validate exponential backoff timing between retries"""
    test_file = tmp_path / "retry_test.py"
    test_file.write_text("# Retry test file\n")
    
    resolve_times = []
    
    def tracked_resolve(self):
        resolve_times.append(time.monotonic())
        if len(resolve_times) < 3:  # Fail first two attempts
            raise OSError(errno.ETIMEDOUT, "Simulated timeout")
        return self._flavour.resolve(self)

    monkeypatch.setattr(pathlib.Path, "resolve", tracked_resolve)
    
    start_time = time.monotonic()
    count_lines_of_code(tmp_path)
    duration = time.monotonic() - start_time
    
    # Verify retry delays (should be ~1s and ~2s)
    assert len(resolve_times) == 3
    delays = [
        resolve_times[1] - resolve_times[0],
        resolve_times[2] - resolve_times[1]
    ]
    assert 0.9 < delays[0] < 1.1, f"First delay was {delays[0]}"
    assert 1.9 < delays[1] < 2.1, f"Second delay was {delays[1]}"
    assert 2.5 < duration < 3.5, f"Total duration was {duration}"


def test_mixed_network_errors(tmp_path, monkeypatch):
    """Test handling of different error types across retries"""
    test_file = tmp_path / "mixed_errors.py"
    test_file.write_text("# Mixed errors test\n")
    
    error_sequence = [
        OSError(errno.ETIMEDOUT, "Timeout"),
        OSError(errno.EHOSTUNREACH, "Host unreachable"),
        OSError(errno.EACCES, "Permission denied")
    ]
    
    def resolve_with_errors(self):
        if error_sequence:
            err = error_sequence.pop(0)
            raise err
        return self._flavour.resolve(self)
    
    monkeypatch.setattr(pathlib.Path, "resolve", resolve_with_errors)
    
    with pytest.raises(OSError) as exc_info:
        count_lines_of_code(tmp_path)
    
    assert exc_info.value.errno == errno.EACCES


def _create_delayed_resolve(original):
    """Create resolve function with simulated timeout errors"""
    import errno

    def delayed_resolve(self, *args, **kwargs):
        for attempt in range(3):
            if attempt == 2:  # Success on final attempt
                return original(self, *args, **kwargs)

            try:
                raise OSError(errno.ETIMEDOUT, "Simulated network timeout")
            except OSError as e:
                if attempt == 1:  # Final error on penultimate attempt
                    raise OSError(errno.EHOSTUNREACH, "Final timeout") from e
                time.sleep(0.5 * (attempt + 1))
        return None

    return delayed_resolve


@contextlib.contextmanager
def _timeout_context():
    """Context manager for timeout measurement"""
    start = time.monotonic()
    yield
    duration = time.monotonic() - start
    assert duration < 3, "Timeout handling failed"
