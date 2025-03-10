import pytest
from project_watch.main import count_lines_of_code, get_pylint_score, get_pytest_results

PERF_THRESHOLDS = {
    "count_lines_small": 0.1,  # seconds
    "count_lines_large": 1.0,
    "pylint_score": 2.0,
    "pytest_results": 2.0,
}


@pytest.fixture(name="large_project")
def large_project_fixture(tmp_path):
    # Create 1000 Python files with 10 lines each
    for i in range(1000):
        file = tmp_path / f"file_{i}.py"
        file.write_text("\n".join([f"# Line {j}" for j in range(10)]))
    return tmp_path


def test_count_lines_performance_small(benchmark):
    # Test small project performance
    result = benchmark(count_lines_of_code)
    assert result >= 0
    assert benchmark.stats.stats.mean < PERF_THRESHOLDS["count_lines_small"]


def test_count_lines_performance_large(benchmark, large_project):
    # Test large project performance
    result = benchmark(count_lines_of_code, large_project)
    assert result == 10000  # 1000 files * 10 lines
    assert benchmark.stats.stats.mean < PERF_THRESHOLDS["count_lines_large"]


def test_pylint_score_performance(benchmark):
    # Test pylint scoring performance
    result = benchmark(get_pylint_score)
    assert 0 <= result <= 10
    assert benchmark.stats.stats.mean < PERF_THRESHOLDS["pylint_score"]


def test_pytest_results_performance(benchmark):
    # Test pytest results parsing performance
    result = benchmark(get_pytest_results)
    assert isinstance(result, dict)
    assert benchmark.stats.stats.mean < PERF_THRESHOLDS["pytest_results"]
