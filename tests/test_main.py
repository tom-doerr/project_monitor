"""Unit tests for project monitoring functionality"""
from project_watch.main import get_project_stats
from datetime import datetime

def test_get_project_stats_structure():
    stats = get_project_stats()
    assert isinstance(stats["pylint"], float)
    assert isinstance(stats["pytest"], dict)
    assert isinstance(stats["loc"], int)
    assert isinstance(stats["last_updated"], datetime)

def test_pylint_score_range():
    score = get_project_stats()["pylint"]
    assert 0.0 <= score <= 10.0

def test_loc_positive():
    assert get_project_stats()["loc"] >= 0
