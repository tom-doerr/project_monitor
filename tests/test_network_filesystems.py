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


def test_network_retry_backoff(tmp_path, monkeypatch):
    """Validate exponential backoff timing between retries"""
    test_file = tmp_path / "retry_test.py"
    test_file.write_text("# Retry test file\n")

    def create_tracked_resolver():
        resolve_times = []
        original_resolve = pathlib.Path.resolve
        
        def tracked_resolve(self):
            resolve_times.append(time.monotonic())
            if len(resolve_times) < 3:
                raise OSError(errno.ETIMEDOUT, "Simulated timeout")
            return original_resolve(self)
            
        return resolve_times, tracked_resolve

    resolve_times, resolver = create_tracked_resolver()
    monkeypatch.setattr(pathlib.Path, "resolve", resolver)

    # Verify retry delays (should be ~1s and ~2s)
    assert len(resolve_times) == 3
    first_delay = resolve_times[1] - resolve_times[0]
    second_delay = resolve_times[2] - resolve_times[1]

    assert 0.9 < first_delay < 1.1, f"First delay was {first_delay}"
    assert 1.9 < second_delay < 2.1, f"Second delay was {second_delay}"

    total_time = time.monotonic() - start_time
    assert 2.5 < total_time < 3.5, f"Total duration was {total_time}"


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

            try:
                raise OSError(errno.ETIMEDOUT, "Simulated network timeout")
            except OSError as e:
                if attempt == 1:  # Final error on penultimate attempt
                    raise OSError(errno.EHOSTUNREACH, "Final timeout") from e
                time.sleep(0.5 * (attempt + 1))

    return delayed_resolve


@contextlib.contextmanager
def _timeout_context():
    """Context manager for timeout measurement"""
    start = time.monotonic()
    yield
    duration = time.monotonic() - start
    assert duration < 3, "Timeout handling failed"
