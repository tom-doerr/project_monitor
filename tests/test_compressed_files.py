import io
import zipfile
import tarfile
from pathlib import Path
from project_watch import count_lines_of_code

def create_zip_with_files(tmp_path: Path, content: str) -> Path:
    zip_path = tmp_path / "test.zip"
    with zipfile.ZipFile(zip_path, 'w') as zf:
        zf.writestr("file1.py", content)
        zf.writestr("nested/file2.py", content)
    return zip_path

def create_tar_with_files(tmp_path: Path, content: str) -> Path:
    tar_path = tmp_path / "test.tar.gz"
    with tarfile.open(tar_path, "w:gz") as tf:
        info = tarfile.TarInfo("file1.py")
        info.size = len(content)
        tf.addfile(info, io.BytesIO(content.encode()))
        
        info = tarfile.TarInfo("nested/file2.py")
        info.size = len(content.encode())  # Use encoded length
        tf.addfile(info, io.BytesIO(content.encode()))
    return tar_path

def test_zip_file_handling(tmp_path: Path):
    content = "print('test')\n" * 10
    zip_path = create_zip_with_files(tmp_path, content)
    assert count_lines_of_code(zip_path) == 20  # 10 lines per file × 2 files

def test_tar_file_handling(tmp_path: Path):
    content = "# Valid Python\n" * 5
    tar_path = create_tar_with_files(tmp_path, content)
    assert count_lines_of_code(tar_path) == 10  # 5 lines per file × 2 files

def test_nested_archives(tmp_path: Path):
    inner_content = "import os\n" * 3
    inner_zip = create_zip_with_files(tmp_path, inner_content)
    
    outer_content = "import sys\n" * 4
    outer_zip = create_zip_with_files(tmp_path, outer_content)
    
    assert count_lines_of_code(inner_zip) == 6  # 3 lines × 2 files
    assert count_lines_of_code(outer_zip) == 8  # 4 lines × 2 files
