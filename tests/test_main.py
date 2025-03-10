"""Unit tests for project monitoring functionality"""

from datetime import datetime
from src.project_watch.main import get_project_stats


def test_get_project_stats_structure():
    """Verify the structure and types of the project stats dictionary."""
    stats = get_project_stats()
    assert isinstance(stats["pylint"], float)
    assert isinstance(stats["pytest"], dict)
    assert isinstance(stats["loc"], int)
    assert isinstance(stats["last_updated"], datetime)


def test_pylint_score_range():
    """Ensure pylint score is within valid 0-10 range."""
    score = get_project_stats()["pylint"]
    assert 0.0 <= score <= 10.0


def test_loc_positive():
    """Verify lines of code count is non-negative."""
    assert get_project_stats()["loc"] >= 0
