from unittest.mock import patch, ANY
import subprocess
from subprocess import CompletedProcess
from project_watch.main import get_pylint_score  # pylint: disable=no-name-in-module


def test_get_pylint_score_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at 9.50/10",
            stderr="",
        )
        assert get_pylint_score() == 9.5


def test_get_pylint_score_minimum():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at 0.0/10",
            stderr="",
        )
        assert get_pylint_score() == 0.0


def test_get_pylint_score_maximum():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at 10.0/10",
            stderr="",
        )
        assert get_pylint_score() == 10.0


def test_get_pylint_score_invalid_output():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="No score here",
            stderr="Also no score",
        )
        assert get_pylint_score() == 0.0


def test_get_pylint_score_malformed_number():
    with patch("subprocess.run") as mock_run, patch("logging.debug") as mock_debug:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at 9.5.0/10",  # Invalid number format
            stderr="",
        )
        assert get_pylint_score() == 0.0
        mock_debug.assert_called_with(
            "Invalid pylint score format: %s - %s", "9.5.0", ANY
        )


def test_get_pylint_score_above_max():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at 12.0/10 (previous run: 9.09/10, +0.01)",
            stderr="Rated at 15.0/10 in stderr",  # Test max of both outputs
        )
        assert get_pylint_score() == 10.0
        mock_run.assert_called_once_with(
            ANY, capture_output=True, check=False, cwd=ANY, text=True, timeout=15
        )


def test_get_pylint_score_below_min():
    with patch("subprocess.run") as mock_run, patch("logging.debug") as mock_debug:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at -5.0/10",
            stderr="Rated at -2.5/10",  # Test min of both outputs
        )
        assert get_pylint_score() == 0.0
        mock_debug.assert_called_with("Pylint error: %s", ANY)


def test_get_pylint_score_at_upper_bound():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="Your code has been rated at 10.0/10",
            stderr="",
        )
        assert get_pylint_score() == 10.0


def test_get_pylint_score_at_lower_bound():
    with patch("subprocess.run") as mock_run, patch("logging.debug") as mock_debug:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=32,  # Over threshold
            stdout="Your code has been rated at 0.0/10",
            stderr="",
        )
        assert get_pylint_score() == 0.0
        mock_debug.assert_called_with("Pylint error: %s", ANY)


def test_get_pylint_score_error(caplog):
    with patch("subprocess.run") as mock_run:
        mock_run.side_effect = Exception("Pylint failed")
        mock_run.return_value = None  # Ensure clean state
        assert get_pylint_score() == 0.0
        assert any(
            "Pylint error: Pylint failed" in rec.message for rec in caplog.records
        )
        mock_run.assert_called_once_with(
            ANY, capture_output=True, check=False, cwd=ANY, text=True, timeout=15
        )


def test_get_pylint_score_from_stderr():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="No score here",
            stderr="Your code has been rated at 7.5/10",
        )
        assert get_pylint_score() == 7.5


def test_get_pylint_score_high_return_code():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = CompletedProcess(
            args=[],
            returncode=32,  # Above threshold (32 > 31)
            stdout="Your code has been rated at 8.5/10",
            stderr="",
        )
        assert get_pylint_score() == 0.0
        mock_run.assert_called_once_with(
            ANY, capture_output=True, check=False, cwd=ANY, text=True, timeout=15
        )


def test_get_pylint_score_empty_output():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        )
        assert get_pylint_score() == 0.0


def test_get_pylint_score_non_zero_exit_success_output():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = CompletedProcess(
            args=[],
            returncode=1,
            stdout="Your code has been rated at 9.5/10",
            stderr="",
        )
        assert get_pylint_score() == 9.5


def test_get_pylint_score_multiple_matches():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = CompletedProcess(
            args=[], returncode=0, stdout="rated at 5/10\nrated at 8/10", stderr=""
        )
        assert get_pylint_score() == 8.0


def test_pylint_timeout_handling():
    with patch("subprocess.run") as mock_run, patch("logging.warning") as mock_warn:
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=[], timeout=15)
        score = get_pylint_score()
        assert score == 0.0
        mock_warn.assert_called_with("Pylint timed out after 15 seconds")
