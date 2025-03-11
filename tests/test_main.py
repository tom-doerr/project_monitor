from datetime import datetime
from unittest.mock import patch

import pytest
from project_watch.main import (
    get_project_stats,
    get_pylint_score,
    count_lines_of_code,
    get_pytest_results,
)

# Test configuration and fixtures


@pytest.fixture(name="_mock_stats")
def mock_stats_fixture() -> dict:
    return {
        "pylint": 8.5,
        "pytest": {"passed": 10, "failed": 0, "skipped": 0},
        "loc": 150,
        "last_updated": datetime.now(),
    }


def test_get_project_stats_aggregation(_mock_stats):
    """Verify all metrics are properly combined"""
    with patch("project_watch.main.get_project_stats") as mock_get:
        mock_get.return_value = _mock_stats
        stats = get_project_stats()
        assert isinstance(stats["pylint"], float)
        assert isinstance(stats["pytest"], dict)
        assert isinstance(stats["loc"], int)
        assert isinstance(stats["last_updated"], datetime)


def test_pylint_returns_valid_score_range(_mock_stats):
    with patch("project_watch.main.get_pylint_score") as mock_pylint:
        mock_pylint.return_value = _mock_stats["pylint"]
        score = get_pylint_score()
        assert 0.0 <= score <= 10.0


def test_loc_returns_non_negative_count(_mock_stats):
    # Should never return negative lines of code
    with patch(
        "project_watch.main.count_lines_of_code", return_value=_mock_stats["loc"]
    ):
        assert count_lines_of_code() >= 0


def test_pytest_results_contain_required_keys(_mock_stats):
    with patch("project_watch.main.get_project_stats") as mock_stats:
        mock_stats.return_value = _mock_stats
        pytest_results = get_project_stats()["pytest"]
        assert "passed" in pytest_results
        assert "failed" in pytest_results
        assert "skipped" in pytest_results


def test_handles_subprocess_failures_gracefully():
    # Should return safe defaults when subprocess fails
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Subprocess failed")
        # Test both functions that use subprocess
        assert get_pylint_score() == 0.0
        assert get_pytest_results().get("error", "").startswith("Subprocess failed")
        assert count_lines_of_code() == 0


def test_file_scanning_edge_cases(tmp_path):
    """Test LOC counting with edge case files"""
    # Create test files
    (tmp_path / "empty.py").touch()

    huge_file = tmp_path / "huge.py"
    huge_file.write_text("\n".join(["pass"] * 10000))

    (tmp_path / "ignore.txt").touch()  # Non-Python file

    # Verify counts while ignoring non-Python files
    assert (
        count_lines_of_code(tmp_path) == 10000
    ), "Should count lines in Python files only"


def test_handles_invalid_pytest_json():
    """Verify JSON parsing error handling"""
    with patch("subprocess.run") as mock_run:
        # Deliberately malformed JSON with unclosed string
        mock_run.return_value.stdout = '{"passed": 3, "failed": "incomplete'
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0

        results = get_pytest_results()
        assert "error" in results, "Should have error key"
        assert (
            "JSON" in results["error"]
        ), f"Should detect JSON parsing error, got {results['error']}"
        assert results.get("passed", 0) == 0  # Should fall back to text parsing
        assert results.get("failed", 0) == 0  # Default values on parse failure
