import pytest
import os
import sqlite3
import shutil
import tempfile
import uuid
from src.components.FileHasher import FileHasher

@pytest.fixture
def temp_dir():
    dir_path = tempfile.mkdtemp()
    yield dir_path
    shutil.rmtree(dir_path)

@pytest.fixture
def temp_db_path(temp_dir):
    return os.path.join(temp_dir, "dependencies.db")

@pytest.fixture
def file_hasher(temp_db_path):
    fh = FileHasher()
    fh.db_path = temp_db_path
    fh._init_db()
    return fh

def create_test_file(temp_dir, filename, content):
    filepath = os.path.join(temp_dir, filename)
    with open(filepath, 'w') as f:
        f.write(content)
    return filepath

def test_file_hasher_initialization(temp_db_path):
    hasher = FileHasher()
    hasher.db_path = temp_db_path
    hasher._init_db()
    assert os.path.exists(temp_db_path)
    
    # Verify table exists
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_hashes'")
        assert cursor.fetchone() is not None

def test_file_hasher_new_files(file_hasher, temp_dir):
    file1 = create_test_file(temp_dir, "file1.py", "print('hello')")
    file2 = create_test_file(temp_dir, "file2.py", "print('world')")
    
    input_files = [
        {"path": file1, "language": "python", "relative_path": "file1.py"},
        {"path": file2, "language": "python", "relative_path": "file2.py"}
    ]
    
    proj_name = f"test_proj_{uuid.uuid4().hex}"
    result = file_hasher.run(files=input_files, working_dir=temp_dir, project_name=proj_name)
    
    # Both files are new, so both should be returned
    assert len(result["files"]) == 2
    assert result["working_dir"] == temp_dir
    
    # Hashes should be returned in pending_hashes, not written to DB yet
    assert len(result["pending_hashes"]) == 2

def test_file_hasher_unchanged_files(file_hasher, temp_dir):
    file1 = create_test_file(temp_dir, "file1.py", "print('hello')")
    
    input_files = [
        {"path": file1, "language": "python", "relative_path": "file1.py"}
    ]
    
    proj_name = f"test_proj_{uuid.uuid4().hex}"
    # First run: should process the file
    result1 = file_hasher.run(files=input_files, working_dir=temp_dir, project_name=proj_name)
    assert len(result1["files"]) == 1
    assert "file1.py" in result1["pending_hashes"]
    
    # Simulate FileHashSaver writing the hash
    with sqlite3.connect(file_hasher.db_path) as conn:
        conn.execute("INSERT INTO file_hashes (file_path, git_hash) VALUES (?, ?)", 
                     ("file1.py", result1["pending_hashes"]["file1.py"]))
        conn.commit()
    
    # Second run immediately after: file unchanged, nên return empty list
    result2 = file_hasher.run(files=input_files, working_dir=temp_dir, project_name=proj_name)
    assert len(result2["files"]) == 0

def test_file_hasher_modified_file(file_hasher, temp_dir):
    file1 = create_test_file(temp_dir, "file1.py", "print('hello')")
    
    input_files = [
        {"path": file1, "language": "python", "relative_path": "file1.py"}
    ]
    
    proj_name = f"test_proj_{uuid.uuid4().hex}"
    # First run
    result1 = file_hasher.run(files=input_files, working_dir=temp_dir, project_name=proj_name)
    
    # Simulate FileHashSaver saving the initial state
    with sqlite3.connect(file_hasher.db_path) as conn:
        conn.execute("INSERT INTO file_hashes (file_path, git_hash) VALUES (?, ?)", 
                     ("file1.py", result1["pending_hashes"]["file1.py"]))
        conn.commit()
    
    # Modify the file
    with open(file1, 'w') as f:
        f.write("print('hello world altered')")
        
    # Second run: file changed, so it should be processed again
    result2 = file_hasher.run(files=input_files, working_dir=temp_dir, project_name=proj_name)
    assert len(result2["files"]) == 1
