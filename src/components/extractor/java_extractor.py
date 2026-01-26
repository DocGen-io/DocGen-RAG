import os
from typing import List, Dict, Any
from tree_sitter import QueryCursor

from .base_extractor import BaseASTExtractor

# Assuming QUERIES_DIR is available or passed. 
# For now, let's look it up relative to this file.
QUERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'extractor', 'queries'
)

class JavaASTExtractor(BaseASTExtractor):
    def __init__(self):
        super().__init__('java')

    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        query_path = os.path.join(QUERIES_DIR, 'controllers', 'java.scm')
        query = self._load_query(query_path)
        if not query: return []

        tree, code_bytes = self.parse_file(file_path)
        if not tree or not code_bytes: return []

        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

        class_map = {} 

        for _, captures in matches:
            
            # --- Class Info ---
            class_name = self._get_capture_text(captures, "class_name", code_bytes)
            if not class_name: continue

            if class_name not in class_map:
                decorator_name = self._get_capture_text(captures, "class_decorator_name", code_bytes)
                if not decorator_name: decorator_name = "Utility"
                
                base_path = self._get_capture_text(captures, "class_decorator_path", code_bytes)
                if not base_path:
                    base_path = ""

                class_map[class_name] = {
                    "class_name": class_name,
                    "class_type": decorator_name,
                    "base_path": base_path,
                    "methods": []
                }
            
            # --- Method Info ---
            if "method_name" in captures:
                method_name = self._get_capture_text(captures, "method_name", code_bytes)
                m_def_node = captures["method_definition"][0] if "method_definition" in captures else None
                
                existing_methods = [m["method_name"] for m in class_map[class_name]["methods"]]
                if method_name in existing_methods:
                    continue

                m_decorator = self._get_capture_text(captures, "method_decorator_name", code_bytes)
                
                is_api = False
                method_type = None
                method_path = None
                
                if m_decorator:
                    if m_decorator.endswith("Mapping"):
                        is_api = True
                        method_type = m_decorator.replace("Mapping", "")
                        if method_type == "Request": method_type = "All"
                    
                    method_path = self._get_capture_text(captures, "method_decorator_path", code_bytes)
                
                method_data = {
                    "method_name": method_name,
                    "method_type": method_type,
                    "is_api_route": is_api,
                    "method_path": method_path,
                    "method_definition": self._get_text(m_def_node, code_bytes) if m_def_node else ""
                }
                
                class_map[class_name]["methods"].append(method_data)
        results = list(class_map.values())

        self.handle_extractor_output(results, file_path)
        return results
