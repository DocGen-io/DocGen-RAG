"""
AST Extractor - OOP Implementation.

Uses tree-sitter query files (.scm) for extraction.
"""

import os
import json
from typing import Tuple, Optional, List, Dict, Any
from tree_sitter import Language, Parser, Tree, Query,QueryCursor
from tree_sitter_language_pack import get_language

from src.components.LanguageFinder import LanguageFinder
from src.services.framework_detector import FrameworkDetector

# Configuration
APIS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'apis-test/nestjs')
AST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ast')

class ASTExtractor:
    """
    Extracts AST chunks from source files using tree-sitter queries.
    
    - Handles only AST parsing and extraction
    - Language support via tree_sitter_language_pack
    - Uses .scm query files from src/components/extractor/queries/
    """

    QUERIES_DIR = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'components', 'extractor', 'queries'
    )

    def __init__(self, language_finder: Optional[LanguageFinder] = None):
        """Initialize with optional dependency injection."""
        self._language_finder = language_finder or LanguageFinder()
        self._language_cache: Dict[str, Language] = {}
        self._query_cache: Dict[str, Query] = {}

    def _get_language(self, language_name: str) -> Optional[Language]:
        """Load and cache tree-sitter language object."""
        if language_name in self._language_cache:
            return self._language_cache[language_name]

        try:
            lang = get_language(language_name)
            if lang:
                self._language_cache[language_name] = lang
                return lang
        except Exception as e:
            print(f"Error loading language {language_name}: {e}")
            pass
        return None

    def _load_query(self, query_path: str, language: Language) -> Optional[Query]:
        """Load and cache a tree-sitter query from .scm file."""
        if query_path in self._query_cache:
            return self._query_cache[query_path]

        try:
            with open(query_path, 'r', encoding='utf-8') as f:
                query_text = f.read()
            query = Query(language, query_text)
           
            self._query_cache[query_path] = query
            return query
        except Exception as e:
            print(f"Error loading query {query_path}: {e}")
            return None

    def parse_file(self, file_path: str, language: Optional[str] = None) -> Tuple[Optional[Tree], Optional[str]]:
        """
        Parse a file and return its AST tree and source code.
        """
        if language is None:
            language = self._language_finder.detect(file_path)
            if language == 'unknown':
                return None, None

        lang_obj = self._get_language(language)
        if not lang_obj:
            return None, None

        try:
            parser = Parser(lang_obj)
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
            tree = parser.parse(bytes(code, 'utf8'))
            return tree, code
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None, None

    def _get_node_text(self, node, code_bytes: bytes) -> str:
        """Extract text content from an AST node."""
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')

    def extract_by_query(
        self,
        file_path: str,
        query_type: str = 'controllers'
    ) -> List[Dict[str, Any]]:
        """
        Extract chunks using tree-sitter query files.
        """
        language = self._language_finder.detect(file_path)
        if language == 'unknown':
            return []

        # Build query file path
        # TODO: Handle mappings if language string differs from filename
        query_file = os.path.join(self.QUERIES_DIR, query_type, f'{language}.scm')
        if not os.path.exists(query_file):
            # print(f"Query file not found for {language}: {query_file}")
            return []

        tree, code = self.parse_file(file_path, language)
        if not tree or not code:
            return []

        lang_obj = self._get_language(language)
        if not lang_obj: 
            return []
            
        query = self._load_query(query_file, lang_obj)
        if not query:
            return []

        code_bytes = bytes(code, 'utf8')
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

        results = []
        current_class = None

        # Helper to safely extract text
        def get_text(captures, key, default=None):
            if key not in captures: return default
            node = captures[key][0]
            return code_bytes[node.start_byte:node.end_byte].decode('utf8').strip("'\"")

        for _, captures in matches:
            # --- HANDLE CLASS MATCH ---
            if "class_name" in captures:
                c_node = captures["class_node"][0]
                decorator = get_text(captures, "class_decorator_name")
                
                current_class = {
                    "class_name": get_text(captures, "class_name"),
                    "class_type": decorator if decorator else "Utility",
                    "base_path": get_text(captures, "class_decorator_path", "/"),
                    "methods": [],
                    "_start": c_node.start_byte,
                    "_end": c_node.end_byte
                }
                results.append(current_class)

            # --- HANDLE METHOD MATCH ---
            elif "method_name" in captures and current_class:
                m_def = captures["method_definition"][0]
                
                # Ensure method is inside current class range
                if m_def.start_byte > current_class["_start"] and m_def.end_byte < current_class["_end"]:
                    m_decorator = get_text(captures, "method_decorator_name")
                    
                    # Condition: Only assign type if it's a known NestJS HTTP Verb
                    is_api = m_decorator in ["Get", "Post", "Put", "Delete", "Patch"]
                    
                    method_data = {
                        "method_name": get_text(captures, "method_name"),
                        "method_type": m_decorator if is_api else None, # Only populated if API
                        "is_api_route": is_api,
                        "method_path": get_text(captures, "method_decorator_path") if is_api else None,
                        "method_definition": get_text(captures, "method_definition")
                    }
                    current_class["methods"].append(method_data)

        # Final cleanup: Remove helper range keys
        for c in results:
            c.pop("_start", None)
            c.pop("_end", None)

        # Only return classes that have at least one method
        final_results = [c for c in results if c["methods"]]
        return final_results


def process_directory(input_dir, output_dir=None):
    """
    Process directory using ASTExtractor and queries.
    """
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    print(f"Scanning {input_dir}...")
    
    # Framework validation
    framework_finder = FrameworkDetector()
    detected_framework = framework_finder.detect(input_dir)
    print(f"Detected Framework: {detected_framework}")
    
    if detected_framework == "Unknown":
        print("Error: this code base does not create REST API endpoints.")
        raise ValueError("this code base does not create REST API endpoints")

    extractor = ASTExtractor()
    all_ast_data = []

    for root, dirs, files in os.walk(input_dir):
        # exclusions
        if 'node_modules' in dirs: dirs.remove('node_modules')
        
        for file in files:
            file_path = os.path.join(root, file)
            # extract_by_query handles language detection internally
            chunks = extractor.extract_by_query(file_path, query_type='controllers')
            if chunks:
                print(f"\nProcessing {file}...")
                print(f"File: {file_path}")
                print(f"Chunks found: {len(chunks)}")
                # Print json output for verification
                print(json.dumps(chunks, indent=2))
                
                # Stop after the first successful file as requested
                all_ast_data.append(chunks)


    return all_ast_data

if __name__ == "__main__":
    process_directory(APIS_DIR, AST_DIR)
