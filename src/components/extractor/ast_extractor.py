import os
import json
from typing import List, Dict, Any, Optional

from src.components.LanguageFinder import LanguageFinder
from src.services.framework_detector import FrameworkDetector

from .java_extractor import JavaASTExtractor
from .typescript_extractor import TypeScriptASTExtractor
from .python_extractor import PythonASTExtractor

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
        }

    def extract_by_query(self, file_path: str, query_type: str = 'controllers') -> List[Dict[str, Any]]:
        language = self._language_finder.detect(file_path)
        if language == 'unknown':
            return []
        
        if language in self._extractors:
            return self._extractors[language].extract(file_path)
        
        return []

def process_directory(input_dir, output_dir=None):
    """
    Process directory using ASTExtractor and queries.
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Scanning {input_dir}...")
    
    framework_finder = FrameworkDetector()
    detected_framework = framework_finder.detect(input_dir)
    print(f"Detected Framework: {detected_framework}")
    
    if detected_framework == "Unknown":
        print("Error: this code base does not create REST API endpoints.")
        pass

    extractor = ASTExtractor()
    all_ast_data = []

    for root, dirs, files in os.walk(input_dir):
        if 'node_modules' in dirs: dirs.remove('node_modules')
        if '.git' in dirs: dirs.remove('.git')
        
        for file in files:
            file_path = os.path.join(root, file)
            chunks = extractor.extract_by_query(file_path, query_type='controllers')
            if chunks:
                print(f"\nProcessing {file}...")
                print(f"File: {file_path}")
                print(f"Chunks found: {len(chunks)}")
                print(json.dumps(chunks, indent=2))
                all_ast_data.append(chunks)

    return all_ast_data

def main():
    APIS_TEST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'apis-test')
    AST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'ast')
    
    SPRINGBOOT_DIR = os.path.join(APIS_TEST_DIR, 'springboot')
    if os.path.exists(SPRINGBOOT_DIR):
         process_directory(SPRINGBOOT_DIR, AST_DIR)

    DJANGO_DIR = os.path.join(APIS_TEST_DIR, 'django')
    if os.path.exists(DJANGO_DIR):
         process_directory(DJANGO_DIR, AST_DIR)

if __name__ == "__main__":
    main()
