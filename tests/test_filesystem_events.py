import time
import pytest
from pathlib import Path
from watchdog.observers import Observer
from project_watch.main import ProjectWatcher

def test_file_event_streaming(tmp_path: Path):
    """Validate detection of create/modify/delete events."""
    test_file = tmp_path / "test_file.txt"
    event_log = []
    
    def callback(event_type: str, path: str):
        event_log.append((event_type, path))
    
    observer = Observer()
    watcher = ProjectWatcher(callback)
    observer.schedule(watcher, str(tmp_path), recursive=True)
    observer.start()
    
    try:
        # Test create
        test_file.touch()
        time.sleep(0.1)
        
        # Test modify
        test_file.write_text("content")
        time.sleep(0.1)
        
        # Test delete
        test_file.unlink()
        time.sleep(0.1)
        
        assert len(event_log) >= 3, "Should detect create/modify/delete"
        assert any("created" in e[0] for e in event_log), "Missing create event"
        assert any("modified" in e[0] for e in event_log), "Missing modify event"
        assert any("deleted" in e[0] for e in event_log), "Missing delete event"
    finally:
        observer.stop()
        observer.join()

def test_latency_threshold(tmp_path: Path):
    """Verify event coalescing within 100ms window."""
    test_file = tmp_path / "rapid.txt"
    event_count = 0
    
    def callback(event_type: str, path: str):
        nonlocal event_count
        event_count += 1
    
    observer = Observer()
    watcher = ProjectWatcher(callback)
    observer.schedule(watcher, str(tmp_path), recursive=True)
    observer.start()
    
    try:
        # Rapid sequential writes
        for _ in range(5):
            test_file.touch(exist_ok=True)
            time.sleep(0.05)
            
        time.sleep(0.2)  # Wait for coalescing
        assert 1 <= event_count <= 2, "Should coalesce rapid updates"
    finally:
        observer.stop()
        observer.join()
