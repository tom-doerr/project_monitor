from unittest.mock import patch
from project_watch.main import (
    get_pytest_results,
)  # pylint: disable=import-error,no-name-in-module


def test_get_pytest_results_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = """
            3 passed, 1 warning in 0.12s
        """
        result = get_pytest_results()
        assert result["passed"] == 3
        assert result["time"] == 0.12


def test_handles_malformed_pytest_json():
    """Verify JSON parsing with valid text fallback"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = '{"invalid": "json"\n3 passed, 1 failed in 0.5s'
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 0
        results = get_pytest_results()
        assert results["passed"] == 3
        assert results["failed"] == 1
        assert "error" not in results


def test_handles_invalid_pytest_output():
    """Verify error handling for completely invalid output"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = "{invalid: json}"
        mock_run.return_value.stderr = ""
        mock_run.return_value.returncode = 1
        results = get_pytest_results()
        assert "error" in results
        assert "JSON" in results["error"]


def test_get_pytest_results_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "2 failed, 1 error"
        result = get_pytest_results()
        assert result["failed"] == 2
        assert "error" in result
