"""Unit tests for project monitoring functionality"""

from datetime import datetime
from unittest.mock import patch
import pytest
from src.project_watch.main import get_project_stats, get_pylint_score, count_lines_of_code

@pytest.fixture
def mock_stats():
    """Fixture providing sample project stats"""
    return {
        "pylint": 8.5,
        "pytest": {"passed": 10, "failed": 0},
        "loc": 150,
        "last_updated": datetime.now()
    }

def test_get_project_stats_structure(mock_stats):
    """Verify the structure and types of the project stats dictionary."""
    with patch('src.project_watch.main.get_project_stats', return_value=mock_stats):
        stats = get_project_stats()
        assert isinstance(stats["pylint"], float)
        assert isinstance(stats["pytest"], dict)
        assert isinstance(stats["loc"], int)
        assert isinstance(stats["last_updated"], datetime)

def test_pylint_score_range(mock_stats):
    """Ensure pylint score is within valid 0-10 range."""
    with patch('src.project_watch.main.get_pylint_score', return_value=mock_stats["pylint"]):
        score = get_pylint_score()
        assert 0.0 <= score <= 10.0

def test_loc_positive(mock_stats):
    """Verify lines of code count is non-negative."""
    with patch('src.project_watch.main.count_lines_of_code', return_value=mock_stats["loc"]):
        assert count_lines_of_code() >= 0

def test_pytest_results_structure(mock_stats):
    """Verify pytest results contain required keys"""
    with patch('src.project_watch.main.get_project_stats', return_value=mock_stats):
        pytest_results = get_project_stats()["pytest"]
        assert "passed" in pytest_results
        assert "failed" in pytest_results
        assert "skipped" in pytest_results
