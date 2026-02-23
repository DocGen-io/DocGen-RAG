import os
from typing import Callable
from gitignore_parser import parse_gitignore
from .logger import DocGenLogger

logger = DocGenLogger()
def get_llm_ignore_filter(directory: str) -> Callable[[str], bool]:
    """
    Checks for an .llmignore file in the specified directory.
    If found, returns a function that takes a file path and returns True if it should be ignored.
    If not found, returns a dummy function that always returns False.
    """
    ignore_path = os.path.join(directory, '.llmignore')
    
    if os.path.exists(ignore_path):
        logger.info(f"Loaded .llmignore from {ignore_path}")
        try:
            return parse_gitignore(ignore_path)
        except Exception as e:
            logger.warning(f"Failed to parse {ignore_path}: {e}")
            
    # Dummy filter that never ignores anything
    return lambda file_path: False
