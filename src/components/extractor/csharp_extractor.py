import os
from typing import List, Dict, Any
from tree_sitter import QueryCursor

from .base_extractor import BaseASTExtractor

class CSharpASTExtractor(BaseASTExtractor):
    def __init__(self):
        super().__init__('csharp')

        self.language = self._load_language()
        
    def extract(self, file_path: str) -> List[Dict[str, Any]]:
        
        # Re-verify query path
        query_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'extractor', 'queries', 'controllers', 'c_sharp.scm'
        )
        
        query = self._load_query(query_path)
        if not query: 
            return []

        tree, code_bytes = self.parse_file(file_path)
        if not tree or not code_bytes: return []

        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

        class_map = {}

        for _, captures in matches:
            class_name = self._get_capture_text(captures, "class_name", code_bytes)
            if not class_name: continue

            if class_name not in class_map:
                superclass = self._get_capture_text(captures, "superclass", code_bytes)
                
                # Heuristics for Class Type
                class_type = "Utility"
                if "Controller" in class_name or "Controller" in superclass:
                    class_type = "Controller"
                elif "Service" in class_name:
                    class_type = "Service"
                
                # Base Path
                # In C#, [Route("auth")] or [Route("api/[controller]")]
                base_path = self._get_capture_text(captures, "base_path", code_bytes)
                
                # Verify attributes to ensure we found the Route attribute if strictly needed,
                # but our query might catch any string literal in an attribute.
                # The query uses @base_path on string_literal inside attribute_argument.
                # We might capture multiple attributes; usually Route is the one with the path.
                
                class_map[class_name] = {
                    "class_name": class_name,
                    "class_type": class_type,
                    "base_path": base_path,
                    "methods": []
                }

            # --- Method Info ---
            if "method_name" in captures:
                method_name = self._get_capture_text(captures, "method_name", code_bytes)
                m_def = captures["method_definition"][0] if "method_definition" in captures else None
                
                # Deduplication
                existing_methods = [m["method_name"] for m in class_map[class_name]["methods"]]
                if method_name in existing_methods:
                    continue

                # Attributes [HttpPost("login")], [HttpGet]
                # We capture method_attr and method_path
                method_attr = self._get_capture_text(captures, "method_attr", code_bytes)
                method_path = self._get_capture_text(captures, "method_path", code_bytes)

                is_api = False
                method_type = None

                # Determine HTTP verb from attribute
                if method_attr.startswith("Http"):
                    # HttpPost, HttpGet, etc.
                    verb = method_attr.replace("Http", "").upper()
                    if verb in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
                        is_api = True
                        method_type = verb.capitalize() # e.g. Post

                # If class is Service, force is_api to False
                if class_map[class_name]["class_type"] == "Service":
                    is_api = False
                    method_type = None
                elif class_map[class_name]["class_type"] == "Controller" and method_type:
                    is_api = True

                method_data = {
                    "method_name": method_name,
                    "method_type": method_type,
                    "is_api_route": is_api,
                    "method_path": method_path,
                    "method_definition": self._get_text(m_def, code_bytes) if m_def else ""
                }

                class_map[class_name]["methods"].append(method_data)

        results = list(class_map.values())
        return [c for c in results if c["methods"]]
