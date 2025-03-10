import pathlib
import pytest
import random
from src.project_watch.main import count_lines_of_code

def generate_invalid_unicode_path(tmp_path: pathlib.Path) -> pathlib.Path:
    invalid_utf8 = b'\x80\x81\xfe\xff'
    test_file = tmp_path / "invalid_unicode.py"
    test_file.write_bytes(b"# Invalid UTF-8 header\n" + invalid_utf8 + b"\nprint('hello')")
    return test_file

def test_invalid_unicode_files(tmp_path):
    path = generate_invalid_unicode_path(tmp_path)
    assert count_lines_of_code(tmp_path) == 2  # Should count valid lines before invalid bytes

def test_extremely_long_lines(tmp_path):
    test_file = tmp_path / "long_lines.py"
    with test_file.open("w", encoding="utf-8") as f:
        f.write("#" * 100000 + "\n")  # 100k character line
        f.write("print('valid')\n")
    assert count_lines_of_code(tmp_path) == 1  # Should count only the valid line

def test_special_filenames(tmp_path):
    weird_names = [
        " space_prefix.py",
        "tab\tprefix.py",
        "newline\nprefix.py",
        "emoji🐍.py"
    ]
    
    for name in weird_names:
        test_file = tmp_path / name
        test_file.write_text("# Valid file\nprint('hello')\n")
    
    assert count_lines_of_code(tmp_path) == 2 * len(weird_names)
