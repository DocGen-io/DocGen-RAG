import re
import os
import json
import yaml
from abc import ABC, abstractmethod
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
from tree_sitter_language_pack import get_language
from tree_sitter import Language, Parser, Tree, Query
from typing import Tuple, Optional, List, Dict, Any, Union



class BaseASTExtractor(ABC):
    """
    Abstract Base Class for language-specific AST extraction.
    """
    def __init__(self, language_name: str, config_path: str = "config.yaml"):
        self.language_name = language_name
        full_config = load_config(config_path)
        self.config = full_config['ast_extractor']
        self.config['queries'] = full_config.get('queries', {})
        self.logger = DocGenLogger(self.__class__.__name__)
        self.language = self._load_language()
        self.parser = Parser(self.language) if self.language else None
        self.query_cache: Dict[str, Query] = {}


    def _load_language(self) -> Optional[Language]:
        names_to_try = [self.language_name, self.language_name.replace('_', ''), self.language_name.replace('sharp', '_sharp')]
        for name in names_to_try:
            try:
                lang = get_language(name)
                if lang: return lang
            except Exception:
                continue
        self.logger.error(f"Error loading language {self.language_name}", location="_load_language")
        return None

    def _load_query(self, query_path: str) -> Optional[Query]:
        if query_path in self.query_cache:
            return self.query_cache[query_path]

        if not os.path.exists(query_path):
            return None

        try:
            with open(query_path, 'r', encoding='utf-8') as f:
                query_text = f.read()
            
            query = Query(self.language, query_text)
            self.query_cache[query_path] = query
            return query
        except Exception as e:
            self.logger.error(f"Error loading query {query_path}: {e}", location="_load_query")
            return None

    def parse_file(self, file_path: str) -> Tuple[Optional[Tree], Optional[bytes]]:
        if not self.parser:
            return None, None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code_str = f.read()
            code_bytes = bytes(code_str, 'utf8')
            tree = self.parser.parse(code_bytes)
            return tree, code_bytes
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}", location="parse_file")
            return None, None

    def _get_text(self, node, code_bytes: bytes) -> str:
        if not node: return ""
        return code_bytes[node.start_byte:node.end_byte].decode('utf8')

    def _get_capture_text(self, captures: Dict, key: str, code_bytes: bytes, default: str = "") -> str:
        if key not in captures: 
            return default
        node = captures[key][0]
        text = self._get_text(node, code_bytes)
        # remove surrounding quotes if it's a string literal
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
        return text

    def _trim_code(self, code: str) -> str:
        """
        Trim extra newlines from code body.
        Removes excessive consecutive newlines (3+) and trims whitespace.
        """
        if not code:
            return code
        # Replace multiple consecutive newlines with a single newline
        cleaned = re.sub(r'\n{3,}', '\n\n', code)
        # Remove leading/trailing whitespace
        return cleaned.strip()

    def _enrich_chunks(self, chunks: List[Dict[str, Any]], file_name: str) -> List[Dict[str, Any]]:
        """
        Enrich chunks by adding file_name to each class and class_name to each method.
        Also trims excessive newlines from method_definition.
        """
        for class_info in chunks:
            class_name = class_info.get('class_name', 'Unknown')
            # Add file_name to class level
            class_info['file_name'] = file_name
            
            methods = class_info.get('methods', [])
            for method in methods:
                # Add class_name to each method
                method['class_name'] = class_name
                # Add file_name to each method
                method['file_name'] = file_name
                # Trim extra newlines from method_definition
                if 'method_definition' in method:
                    method['method_definition'] = self._trim_code(method['method_definition'])
        
        return chunks

    def handle_extractor_output(self, chunks: List[Dict[str, Any]], file_path: str) -> List[Dict[str, Any]]:
        # Extract file name from path
        file_name = file_path.split('/')[-1] + '.json'
        
        # Enrich chunks with file_name and class_name, and trim newlines
        chunks = self._enrich_chunks(chunks, file_name)

        if self.config['verbose']:
            self.logger.info(json.dumps(chunks, indent=2), location="handle_extractor_output")
        
        if self.config['save_ast']:
            # create directory if not exists
            if not os.path.exists(self.config['save_ast_path']):
                os.makedirs(self.config['save_ast_path'])

            if not chunks:
                self.logger.warning(f"No chunks found for {file_name}", location="handle_extractor_output")
                return []
            
            with open(self.config['save_ast_path'] + "/" + file_name, 'w') as f:
                json.dump(chunks, f, indent=2)
                
            self.logger.info(f"Saved AST to {self.config['save_ast_path'] + '/' + file_name}", location="handle_extractor_output")
        return chunks
    
    @abstractmethod
    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        pass

