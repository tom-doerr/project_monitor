import pytest  # pylint: disable=unused-import
from project_watch.main import count_lines_of_code

def test_long_lines(tmp_path):
    test_file = tmp_path / "long.py"
    content = "# " + "-" * 10_000 + "\nprint('hello')"  # 10k+ line
    test_file.write_text(content)
    
    assert count_lines_of_code(tmp_path) == 2
