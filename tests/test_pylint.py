from unittest.mock import patch
from src.project_watch.main import get_pylint_score  # pylint: disable=import-error,no-name-in-module

def test_get_pylint_score_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "Your code has been rated at 9.50/10"
        assert get_pylint_score("dummy_path") == 9.5

def test_get_pylint_score_error():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Pylint failed")
        assert get_pylint_score("dummy_path") == 0.0
