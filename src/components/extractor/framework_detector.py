import os
from typing import List, Optional,Dict,Any
from src.utils.config_loader import load_config
from tree_sitter import QueryCursor
from src.utils.logger import DocGenLogger
from haystack import component
from src.components.LanguageFinder import LanguageFinder
from .controllers_extractor import ControllersExtractor

@component
class FrameworkDetector:
 
    def __init__(self,config_path:str="config.yaml"):
        self.config = load_config(config_path)
        self.logger = DocGenLogger(self.__class__.__name__)
      
    
    def _extract_file(self, file_metadata: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract AST from a single file."""
        if file_metadata['language'] == 'unknown':
            self.logger.warning(f"Unknown language for file: {file_metadata['path']}", location="_extract_file")
            return []
        
        return ControllersExtractor(file_metadata['language']).extract(file_metadata['path'])
       
    @component.output_types(
        controllers=List[str],
    )
    def run(self, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
            Detect if controllers are present in the project using tree-sitter
            return list of controllers
        """
        controllers = []
        
        for file_metadata in files:
            file_path = file_metadata['path']
            if not os.path.exists(file_path):
                continue
            
            try:
                ast_data = self._extract_file(file_metadata)
                if ast_data:
                    controllers.append(ast_data)
            except Exception as e:
                self.logger.error(f"Error extracting {file_path}: {e}", location="framework_detector.run")
        
        self.logger.info(f"Found {len(controllers)} controllers", location="framework_detector.run")
        return {
            "controllers": controllers,
        }
