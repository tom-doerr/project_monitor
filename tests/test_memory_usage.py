import tracemalloc
import pytest
from project_watch import count_lines_of_code

@pytest.fixture(autouse=True)
def memory_tracker():
    tracemalloc.start()
    yield
    tracemalloc.stop()

def test_no_memory_leak_in_line_counting(tmp_path):
    # Setup: Create sample Python files
    sample_code = "print('test')\n" * 1000
    for i in range(10):
        (tmp_path / f"test_{i}.py").write_text(sample_code)

    # Get baseline memory
    snapshot1 = tracemalloc.take_snapshot()
    
    # Run operation multiple times
    for _ in range(10):
        count_lines_of_code(tmp_path)
    
    # Get comparison snapshot
    snapshot2 = tracemalloc.take_snapshot()
    
    # Calculate memory difference
    top_stats = snapshot2.compare_to(snapshot1, "lineno")
    
    # Verify no single allocation grows without bound
    for stat in top_stats[:5]:
        assert stat.size_diff < 1024 * 1024, \
            f"Memory leak detected: {stat.traceback.format()[-1]} allocated {stat.size_diff} bytes"
