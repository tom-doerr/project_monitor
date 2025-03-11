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
    [  # List comprehension reduces variables
        (tmp_path / f"test_{i}.py").write_text(sample_code)
        for i in range(10)
    ]

    # Combined snapshot and comparison logic
    top_stats = tracemalloc.take_snapshot().compare_to(
        tracemalloc.take_snapshot(),  # Initial snapshot
        "lineno"
    )

    # Check top 5 allocations
    for stat in top_stats[:5]:
        assert stat.size_diff < 1024 * 1024, \
            f"Memory leak detected: {stat.traceback.format()[-1]} allocated {stat.size_diff} bytes"
