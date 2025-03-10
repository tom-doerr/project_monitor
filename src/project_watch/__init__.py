# Package initialization for project_watch
from pathlib import Path
from importlib.metadata import version

__version__ = version("project_watch")
__all__ = ['count_lines_of_code', 'get_pylint_score', 'get_pytest_results', 'get_project_stats']

# Initialize default paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
