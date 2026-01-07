import os
import pytest
from src.services.input_handler import InputHandler

def test_input_handler_local_folder(tmp_path):
    # Create a dummy structure
    source = tmp_path / "source"
    source.mkdir()
    (source / "file.txt").write_text("content")
    
    handler = InputHandler()
    try:
        temp_dir = handler.process_local_folder(str(source))
        assert os.path.exists(temp_dir)
        assert os.path.exists(os.path.join(temp_dir, "file.txt"))
    finally:
        handler.cleanup()
        if handler.temp_dir:
            assert not os.path.exists(handler.temp_dir)

def test_input_handler_invalid_folder():
    handler = InputHandler()
    with pytest.raises(FileNotFoundError):
        handler.process_local_folder("/non/existent/path")
