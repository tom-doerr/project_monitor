from unittest.mock import patch
import subprocess
from project_watch.main import (
    get_pylint_score,
)  # pylint: disable=import-error,no-name-in-module


def test_get_pylint_score_success():
    with patch("subprocess.run") as mock_run:
        # Configure both stdout and stderr to avoid MagicMock errors
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at 9.50/10",
            stderr="",
        )
        assert get_pylint_score() == 9.5


def test_get_pylint_score_error():
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Pylint failed")
        assert get_pylint_score() == 0.0
