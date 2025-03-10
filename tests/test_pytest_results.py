from unittest.mock import patch
from src.project_watch.main import get_pytest_results  # pylint: disable=import-error,no-name-in-module

def test_get_pytest_results_success():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.stdout = """
            3 passed, 1 warning in 0.12s
        """
        result = get_pytest_results()
        assert result["passed"] == 3
        assert result["time"] == 0.12

def test_get_pytest_results_failure():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "2 failed, 1 error"
        result = get_pytest_results()
        assert result["failed"] == 2
        assert "error" in result
