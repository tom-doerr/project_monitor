from project_watch.main import count_lines_of_code


def test_common_binary_extensions(tmp_path):
    # Create test files with binary content
    (tmp_path / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00")
    (tmp_path / "document.pdf").write_text("%PDF-1.4\n...\n%%EOF\n")
    (tmp_path / "binary.exe").write_bytes(b"MZ\x90\x00\x03\x00\x00\x00")

    assert count_lines_of_code() == 0  # Should skip all binary files


def test_mixed_content_files(tmp_path):
    # File with both text and binary content
    mixed_file = tmp_path / "mixed.dat"
    with mixed_file.open("wb") as f:
        f.write(b"Valid text\n\x00\x01\x02\x03\nMore text\n")

    assert count_lines_of_code() == 0  # Should detect binary markers


def test_ambiguous_extensions(tmp_path):
    # Text file with binary extension
    (tmp_path / "code.png").write_text("def test():\n    pass\n")
    # Binary file with text extension
    (tmp_path / "data.txt").write_bytes(b"\x00\x01\x02\x03\x04")

    assert count_lines_of_code() == 2  # Should count only valid text file
