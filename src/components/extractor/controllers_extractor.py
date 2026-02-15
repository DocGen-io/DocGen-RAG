import os
from haystack import component
from typing import List, Optional,Dict,Any
from src.utils.config_loader import load_config
from tree_sitter import QueryCursor
from .base_extractor import BaseASTExtractor
from src.utils.logger import DocGenLogger
logger = DocGenLogger(__name__)


class ControllersExtractor(BaseASTExtractor):
 
    def __init__(self,language_name:str):
        super().__init__(language_name)
        self.query_path = os.path.join(self.config["queries"]["controllers-extractors"], f"{language_name}.scm")


    def extract(self, file_path: str) -> Optional[str]:
        query = self._load_query(self.query_path)

        tree, code_bytes = self.parse_file(file_path)
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)
        for _, captures in matches:
            if captures:
              return file_path
        
        return None
           

 