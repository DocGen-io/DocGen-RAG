import os
from typing import List, Dict, Any
from tree_sitter import QueryCursor

from .base_extractor import BaseASTExtractor

QUERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'extractor', 'queries'
)

class TypeScriptASTExtractor(BaseASTExtractor):
    def __init__(self):
        super().__init__('typescript')

    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        query_path = os.path.join(QUERIES_DIR, 'controllers', 'typescript.scm')
        query = self._load_query(query_path)
        if not query: return []

        tree, code_bytes = self.parse_file(file_path)
        if not tree or not code_bytes: return []

        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)
        
        results = []
        current_class = None
        seen_methods = set()  # Track method byte ranges to avoid duplicates

        for _, captures in matches:
            if "class_name" in captures:
                c_node = captures["class_node"][0]
                decorator = self._get_capture_text(captures, "class_decorator_name", code_bytes)
                
                current_class = {
                    "class_name": self._get_capture_text(captures, "class_name", code_bytes),
                    "class_type": decorator if decorator else "Utility",
                    "base_path": self._get_capture_text(captures, "class_decorator_path", code_bytes, "/"),
                    "methods": [],
                    "_start": c_node.start_byte,
                    "_end": c_node.end_byte
                }
                results.append(current_class)

            # Handle regular method_definition WITH decorator
            elif "method_name" in captures and current_class:
                m_def = captures["method_definition"][0]
                method_key = (m_def.start_byte, m_def.end_byte)
                if method_key in seen_methods:
                    continue
                if not (m_def.start_byte >= current_class["_start"] and m_def.end_byte <= current_class["_end"]):
                    continue
                seen_methods.add(method_key)

                m_decorator = self._get_capture_text(captures, "method_decorator_name", code_bytes)
                is_api = m_decorator in ["Get", "Post", "Put", "Delete", "Patch", "Options", "Head", "All", "MessagePattern"]
                
                method_data = {
                    "method_name": self._get_capture_text(captures, "method_name", code_bytes),
                    "method_type": m_decorator if is_api else None,
                    "is_api_route": is_api,
                    "method_path": self._get_capture_text(captures, "method_decorator_path", code_bytes) if is_api else None,
                    "method_definition": self._get_text(m_def, code_bytes)
                }
                current_class["methods"].append(method_data)

            # Handle regular method_definition WITHOUT decorator
            elif "plain_method_name" in captures and current_class:
                m_def = captures["plain_method_definition"][0]
                method_key = (m_def.start_byte, m_def.end_byte)
                if method_key in seen_methods:
                    continue
                if not (m_def.start_byte >= current_class["_start"] and m_def.end_byte <= current_class["_end"]):
                    continue
                seen_methods.add(method_key)
                
                method_data = {
                    "method_name": self._get_capture_text(captures, "plain_method_name", code_bytes),
                    "method_type": None,
                    "is_api_route": False,
                    "method_path": None,
                    "method_definition": self._get_text(m_def, code_bytes)
                }
                current_class["methods"].append(method_data)

            # Handle arrow function method WITH decorator
            elif "arrow_method_name" in captures and current_class:
                m_def = captures["arrow_method_definition"][0]
                method_key = (m_def.start_byte, m_def.end_byte)
                if method_key in seen_methods:
                    continue
                if not (m_def.start_byte >= current_class["_start"] and m_def.end_byte <= current_class["_end"]):
                    continue
                seen_methods.add(method_key)

                m_decorator = self._get_capture_text(captures, "arrow_method_decorator_name", code_bytes)
                is_api = m_decorator in ["Get", "Post", "Put", "Delete", "Patch", "Options", "Head", "All", "MessagePattern"]
                
                method_data = {
                    "method_name": self._get_capture_text(captures, "arrow_method_name", code_bytes),
                    "method_type": m_decorator if is_api else None,
                    "is_api_route": is_api,
                    "method_path": self._get_capture_text(captures, "arrow_method_decorator_path", code_bytes) if is_api else None,
                    "method_definition": self._get_text(m_def, code_bytes)
                }
                current_class["methods"].append(method_data)

            # Handle arrow function method WITHOUT decorator
            elif "plain_arrow_method_name" in captures and current_class:
                m_def = captures["plain_arrow_method_definition"][0]
                method_key = (m_def.start_byte, m_def.end_byte)
                if method_key in seen_methods:
                    continue
                if not (m_def.start_byte >= current_class["_start"] and m_def.end_byte <= current_class["_end"]):
                    continue
                seen_methods.add(method_key)
                
                method_data = {
                    "method_name": self._get_capture_text(captures, "plain_arrow_method_name", code_bytes),
                    "method_type": None,
                    "is_api_route": False,
                    "method_path": None,
                    "method_definition": self._get_text(m_def, code_bytes)
                }
                current_class["methods"].append(method_data)

        for c in results:
            c.pop("_start", None)
            c.pop("_end", None)

        self.handle_extractor_output(results,file_path)
        return [c for c in results if c["methods"]]
 
