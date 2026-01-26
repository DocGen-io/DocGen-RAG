from abc import ABC, abstractmethod
from typing import Tuple, Optional, List, Dict, Any, Union
import os
from tree_sitter import Language, Parser, Tree, Query
from tree_sitter_language_pack import get_language
import yaml
import json



class BaseASTExtractor(ABC):
    """
    Abstract Base Class for language-specific AST extraction.
    """
    def __init__(self, language_name: str):
        self.language_name = language_name
        self.language = self._load_language()
        self.parser = Parser(self.language) if self.language else None
        self.query_cache: Dict[str, Query] = {}

    def _load_language(self) -> Optional[Language]:
        try:
            return get_language(self.language_name)
        except Exception as e:
            print(f"Error loading language {self.language_name}: {e}")
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
            print(f"Error loading query {query_path}: {e}")
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
            print(f"Error parsing {file_path}: {e}")
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

    def handle_extractor_output(self, chunks: List[Dict[str, Any]],file_path:str) -> List[Dict[str, Any]]:
        # read from config.yaml

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        if config['verbose']:
            print(json.dumps(chunks, indent=2))
        
        if config['save_ast']:
            # create directory if not exists
            file_path = file_path.split('/')[-1] + '.json'

            if(not os.path.exists(config['save_ast_path'])):
                os.makedirs(config['save_ast_path'])

            with open(config['save_ast_path'] + "/" + file_path, 'w') as f:
                json.dump(chunks, f, indent=2)
                
            print(f"Saved AST to {config['save_ast_path'] + '/' + file_path}")
        return chunks
    
    @abstractmethod
    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        pass
