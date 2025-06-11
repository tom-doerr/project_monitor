import time
from pathlib import Path
from watchdog.observers import Observer
from project_watch.main import ProjectWatcher


def test_file_event_streaming(tmp_path: Path):
    """Validate detection of create/modify/delete events."""
    event_log = []

    def _handle_event(event_type: str, path: str) -> None:
        event_log.append((event_type, path))

    with _create_observer(tmp_path, _handle_event) as _:
        # Perform file operations
        test_file = tmp_path / "test_file.txt"
        operations = (
            test_file.touch,
            lambda: test_file.write_text("content"),
            test_file.unlink,
        )
        for op in operations:
            op()

        time.sleep(0.5)  # Allow time for events to propagate

        assert len(event_log) >= 1, "Should detect at least one event"
        detected_events = {e[0] for e in event_log}
        assert detected_events.issuperset(
            {"created", "modified", "deleted"}
        ), f"Missing events in {detected_events}"


def _create_observer(path: Path, callback) -> Observer:
    """Helper to create and start an observer with proper cleanup."""
    observer = Observer()
    watcher = ProjectWatcher(callback)
    observer.schedule(watcher, str(path), recursive=True)
    observer.start()
    return observer


def test_latency_threshold(tmp_path: Path):
    """Verify event coalescing within 100ms window."""
    event_count = 0

    def callback(_event_type: str, _path: str) -> None:
        nonlocal event_count
        event_count += 1

    with _create_observer(tmp_path, callback) as _:
        test_file = tmp_path / "rapid.txt"

        # Rapid sequential writes
        for _ in range(5):
            test_file.touch(exist_ok=True)
            time.sleep(0.05)

        time.sleep(0.2)  # Allow for event coalescing

        assert 1 <= event_count <= 3, f"Unexpected event count {event_count}"
