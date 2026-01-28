import os
import json
from typing import List, Dict, Any, Optional

from src.components.LanguageFinder import LanguageFinder
from src.services.framework_detector import FrameworkDetector

from .java_extractor import JavaASTExtractor
from .typescript_extractor import TypeScriptASTExtractor
from .python_extractor import PythonASTExtractor
from .csharp_extractor import CSharpASTExtractor

class ASTExtractor:
    """
    Facade class that routes to the appropriate language extractor.
    """
    def __init__(self, language_finder: Optional[LanguageFinder] = None):
        self._language_finder = language_finder or LanguageFinder()
        self._extractors = {
            'java': JavaASTExtractor(),
            'typescript': TypeScriptASTExtractor(),
            'python': PythonASTExtractor(),
            'c_sharp': CSharpASTExtractor(),
        }

    def extract_by_query(self, file_path: str) -> List[Dict[str, Any]]:
        language = self._language_finder.detect(file_path)
        if language == 'unknown':
            return []
        
        if language in self._extractors:
            return self._extractors[language].extract(file_path)
        
        return []


def main():
    classExtractor = ASTExtractor()
    APIS_TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'apis-test')
    
    SPRINGBOOT_DIR = os.path.join(APIS_TEST_DIR, 'springboot/AuthController.java')
    classExtractor.extract_by_query(SPRINGBOOT_DIR)
    

if __name__ == "__main__":
    main()
