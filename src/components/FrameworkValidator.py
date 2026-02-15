
from haystack import component
from typing import List, Dict, Any, Optional
import logging

from src.services.framework_detector import FrameworkDetector
from src.utils.config_loader import load_config

logger = logging.getLogger(__name__)

@component
class FrameworkValidator:
    """
    Haystack component that validates the framework of a project.
    Wraps SourceHandler output and FrameworkDetector logic.
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        self.detector = FrameworkDetector()
        self.config = load_config(config_path)
        self.api_frameworks = set(self.config.get("api_frameworks", []))

    @component.output_types(
        files=List[Dict[str, str]],
        working_dir=str,
        framework=str
    )
    def run(self, files: List[Dict[str, str]], working_dir: str):
        """
        Validate framework and pass through file paths if valid.
        
        Args:
            files: List of file metadata from SourceHandler
            working_dir: Working directory of the project
            
        Returns:
            Dict with files, working_dir, and framework if valid.
            Raises ValueError if framework is invalid (stopping pipeline).
        """
        logger.info(f"Validating framework in {working_dir}...")
        framework = self.detector.detect(working_dir)
        logger.info(f"Detected framework: {framework}")
        
        if framework not in self.api_frameworks:
            error_msg = f"Unsupported or no API framework detected: {framework}. Supported: {self.api_frameworks}"
            logger.error(error_msg)
            raise ValueError(error_msg)
            
        return {
            "files": files,
            "working_dir": working_dir,
            "framework": framework
        }
