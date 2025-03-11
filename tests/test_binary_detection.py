from project_watch.main import count_lines_of_code


def test_files_with_null_bytes(tmp_path):
    """Test files containing null bytes are skipped"""
    # Create test files
    # Create test files
    (tmp_path / "valid.py").write_text("print('hello')\n")

    null_file = tmp_path / "null.py"
    with null_file.open("wb") as f:
        f.write(b"print(\x00'null')\n")

    (tmp_path / "binary.py").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")

    result = count_lines_of_code(tmp_path)
    assert result == 1, "Should only count valid.py"


def test_non_py_files_with_code(tmp_path):
    """Test non-.py files are ignored even if they contain code"""
    valid_py = tmp_path / "valid.py"
    valid_py.write_text("x = 1\nx = 2\n")

    js_file = tmp_path / "file.js"
    js_file.write_text("console.log('test');\n")

    result = count_lines_of_code(tmp_path)
    assert result == 2


def test_binary_file_cleanup(tmp_path):
    """Verify binary file handling doesn't leave temp files"""
    temp_file = tmp_path / "tempfile.py"
    temp_file.write_text("temp content")
    initial_file_count = len(list(tmp_path.glob("*")))

    count_lines_of_code(tmp_path)
    assert len(list(tmp_path.glob("*"))) == initial_file_count  # No temp files left


def test_hidden_directories(tmp_path):
    """Test files in hidden directories are skipped"""
    hidden_dir = tmp_path / ".hidden"
    hidden_dir.mkdir()
    (hidden_dir / "test.py").write_text("x = 1\n")

    result = count_lines_of_code(tmp_path)
    assert result == 0, "Should skip hidden directory"
