from pathlib import Path
from project_watch.main import count_lines_of_code


def test_empty_directory(tmp_path: Path):
    """Test line counting in an empty directory"""
    result = count_lines_of_code(tmp_path)
    assert result == 0


def test_directory_with_empty_files(tmp_path: Path):
    """Test directory containing only empty files"""
    empty_file = tmp_path / "empty.py"
    empty_file.touch()

    empty_file2 = tmp_path / "void.py"
    empty_file2.touch()

    assert count_lines_of_code(tmp_path) == 0


def test_mixed_empty_and_code_files(tmp_path: Path):
    """Test directory with mix of empty and valid code files"""
    # Create empty file
    (tmp_path / "empty.py").touch()

    # Create file with content
    code_file = tmp_path / "valid.py"
    code_file.write_text("def test():\n    print('hello')\n")

    assert count_lines_of_code(tmp_path) == 2
