from project_watch.main import count_lines_of_code

def test_mixed_content_files(tmp_path):
    mixed_file = tmp_path / "mixed.dat"
    mixed_file.write_bytes(b"Valid text\x00Binary content\xFF\xFE")
    assert count_lines_of_code(mixed_file) == 0

def test_ambiguous_extensions(tmp_path):
    text_file = tmp_path / "code.png"
    text_file.write_text("Line 1\nLine 2")
    binary_file = tmp_path / "data.txt"
    binary_file.write_bytes(b"\x00\xFFbinary\x00")
    assert count_lines_of_code(text_file) == 2
    assert count_lines_of_code(binary_file) == 0
