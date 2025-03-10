from pathlib import Path
import pytest
import os
from project_watch.main import count_lines_of_code

def test_symlink_to_file(tmp_path: Path):
    """Test behavior with symlink to a real file"""
    real_file = tmp_path / "real.py"
    real_file.write_text("# Valid Python file\nprint('hello')\n")
    
    symlink = tmp_path / "link.py"
    os.symlink(real_file, symlink)
    
    assert count_lines_of_code(tmp_path) == 2

def test_broken_symlink(tmp_path: Path):
    """Test handling of broken symlinks"""
    symlink = tmp_path / "broken_link.py"
    os.symlink("/nonexistent/file.py", symlink)
    
    assert count_lines_of_code(tmp_path) == 0

def test_symlink_to_directory(tmp_path: Path):
    """Test behavior with symlink to a directory"""
    real_dir = tmp_path / "real_dir"
    real_dir.mkdir()
    (real_dir / "test.py").write_text("content")
    
    symlink_dir = tmp_path / "link_dir"
    os.symlink(real_dir, symlink_dir)
    
    # Should count lines in both real and linked directories
    assert count_lines_of_code(tmp_path) == 1

def test_nested_symlinks(tmp_path: Path):
    """Test complex symlink scenarios"""
    real_file = tmp_path / "target.py"
    real_file.write_text("# Target\n")
    
    link1 = tmp_path / "link1.py"
    os.symlink(real_file, link1)
    
    link2 = tmp_path / "link2.py"
    os.symlink(link1, link2)
    
    assert count_lines_of_code(tmp_path) == 1
