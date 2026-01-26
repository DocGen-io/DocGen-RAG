import os
from typing import List, Dict, Any
from tree_sitter import QueryCursor

from .base_extractor import BaseASTExtractor

QUERIES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    'extractor', 'queries'
)

class PythonASTExtractor(BaseASTExtractor):
    def __init__(self):
        super().__init__('python')

    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        query_path = os.path.join(QUERIES_DIR, 'controllers', 'python.scm')
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
            # Some queries might capture class_name multiple times or nested
            if not class_name: continue

            if class_name not in class_map:
                # Type inference
                superclass = self._get_capture_text(captures, "superclass", code_bytes)
                class_type = "Utility"
                
                # Check annotations/decorators if strictly needed, but heuristic based on name/inheritance is often enough for Django
                if superclass == "View" or class_name.endswith("View") or class_name.endswith("ViewSet"):
                    class_type = "Controller" # or View? Java used RestController.
                elif class_name.endswith("Service"):
                    class_type = "Service"

                # Base path is hard to infer from class file alone in Django (it's in urls.py)
                # We'll leave it empty unless captured from a specific decorator (like drf @api_view which isn't here)
                base_path = ""

                class_map[class_name] = {
                    "class_name": class_name,
                    "class_type": class_type,
                    "base_path": base_path,
                    "methods": []
                }

            # --- Method Info ---
            if "method_name" in captures:
                method_name = self._get_capture_text(captures, "method_name", code_bytes)
                
                m_def = captures["method_definition"][0]
                
                # Deduplicate
                existing_methods = [m["method_name"] for m in class_map[class_name]["methods"]]
                if method_name in existing_methods:
                    continue

                # Python/Django: method name often implies type (get, post, put)
                # Or check decorators (like @action in DRF, or @require_http_methods)
                is_api = False
                method_type = None
                method_path = None # Again, paths are usually in urls.py or DRF routers

                lower_name = method_name.lower()
                if lower_name in ["get", "post", "put", "delete", "patch", "options", "head"]:
                    is_api = True
                    method_type = lower_name.capitalize()
                
                # For services, everything is just valid methods, but maybe not API routes directly
                # If class_type is Service, is_api might be false, or true if we treat service methods as operations.
                # Java output for Services had is_api_route: false.
                if class_map[class_name]["class_type"] == "Service":
                    is_api = False
                    method_type = None
                elif class_map[class_name]["class_type"] == "Controller" and method_type:
                    is_api = True # confirmed
                
                # If path not found (standard Django CBV), maybe use method name or empty
                if is_api and not method_path:
                    method_path = "" # Standard CBV dispatch via verb

                method_data = {
                    "method_name": method_name,
                    "method_type": method_type,
                    "is_api_route": is_api,
                    "method_path": method_path,
                    "method_definition": self._get_text(m_def, code_bytes)
                }
                
                class_map[class_name]["methods"].append(method_data)

        # Filter only classes with methods? Java extractor did.
        # But maybe we want empty classes too? sticking to Java behavior
        results = list(class_map.values())
        return [c for c in results if c["methods"]]
