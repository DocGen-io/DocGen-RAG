import os
from typing import List, Dict, Any, Optional
from tree_sitter import QueryCursor, Node
from .base_extractor import BaseASTExtractor


class GeneralExtractor(BaseASTExtractor):
    """
    Unified extractor. Optimized to handle TS, Python, Java, and C# 
    using a single-pass structural mapping.
    """
    def __init__(self, language_name: str):
        super().__init__(language_name)
        self.query_path = os.path.join(self.config["queries"]["general"], f"{language_name}.scm")
        self.CONTAINER_TAGS = ["class_name", "interface_name", "record_name"]
        self.METHOD_TAGS = ["method_name", "method_call"]
    

    def find_parent_container(self,node: Node, structure_map: Dict[int, Dict[str, Any]]) -> Optional[Dict]:
            curr = node.parent
            while curr:
                if curr.id in structure_map:
                    return structure_map[curr.id]
                curr = curr.parent
            return None


    def extract(self, file_path: str, file_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        query = self._load_query(self.query_path)
        tree, code_bytes = self.parse_file(file_path)
        if not all([query, tree, code_bytes]):
            return []

      
        
        structure_map = {}  # node_id -> structure_dict
        global_methods = []
        file_name = os.path.basename(file_path)

        # Single pass execution
        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

      
        for _, captures in matches:
            # 1. Handle Containers (Classes, Interfaces, Records)
            for tag in self.CONTAINER_TAGS:
                if tag in captures:
                    name = self._get_capture_text(captures, tag, code_bytes)
                    # Find the body/declaration node to act as the ID anchor
                    body_node = captures.get(tag.replace("_name", "_body"), 
                                captures.get(tag.replace("_name", "_declaration"), 
                                captures.get(tag.replace("_name", "_node"),
                                captures.get(tag.replace("_name", "_definition"),
                                captures.get(tag, [None])))))[0]
                    
                    if not body_node or body_node.id in structure_map:
                        continue

                    # Determine type based on capture name or content
                    ctype = "Utility"
                    if "interface" in tag: ctype = "Interface"
                    elif "record" in tag: ctype = "Record"
                    elif any(k in name for k in ["Controller", "Service", "Resolver"]):
                        ctype = next(k for k in ["Controller", "Service", "Resolver"] if k in name)

                    # Extract base path from decorator if available
                    base_path = ""
                    if "class_decorator_path" in captures:
                        base_path = self._get_capture_text(captures, "class_decorator_path", code_bytes)
                        # Clean up quotes if present
                        base_path = base_path.strip("'\"")

                    # Get relative path from metadata or fallback
                    rel_path = file_path
                    if file_metadata and 'relative_path' in file_metadata:
                        rel_path = file_metadata['relative_path']
                    else:
                        try:
                            rel_path = os.path.relpath(file_path, os.getcwd())
                        except ValueError:
                            pass

                    structure_map[body_node.id] = {
                        "class_name": name,
                        "class_type": ctype,
                        "base_path": base_path,
                        "methods": [],
                        "file_name": file_name,
                        "file_path": rel_path
                    }


            # 2. Handle Methods and Functions
            for tag in self.METHOD_TAGS:
                
            
                if tag in captures:
                    m_name = self._get_capture_text(captures, tag, code_bytes)
                    m_body = captures.get(tag.replace("_name", "_body"), 
                             captures.get("method_definition", [None]))[0]
                    
                    if not m_body: continue

                    parent = self.find_parent_container(m_body, structure_map)
                    is_api = (tag == "method_call") or (parent and parent["class_type"] == "Controller")

                    method_data = {
                        "method_name": m_name,
                        "method_type": None,
                        "is_api_route": is_api,
                        "method_path": None,
                        "method_definition": self._trim_code(self._get_text(m_body, code_bytes))
                    }

                    if parent:
                        if not any(m["method_name"] == m_name for m in parent["methods"]):
                            parent["methods"].append(method_data)
                    else:
                        global_methods.append(method_data)

            
            # 3. Handle Decorators (Apply to parent container or methods)
            for d_tag in ["decorator", "decorators", "method_decorator", "arrow_method_decorator"]:
                if d_tag in captures:
                    d_node = captures[d_tag][0]
                    d_text = self._get_text(d_node, code_bytes)
                    parent = self.find_parent_container(d_node, structure_map)
                    
                    if parent:
                        # If decorator contains a Verb, mark the last added method as an API route
                        # If decorator contains a Verb, mark the last added method as an API route
                        # Check for both Title Case (NestJS, .NET) and lowercase (FastAPI) verbs
                        verb = next((v for v in ["Get", "Post", "Put", "Delete", "Patch", "get", "post", "put", "delete", "patch"] if v in d_text), None)
                        if verb and parent["methods"]:
                            parent["methods"][-1]["is_api_route"] = True
                            parent["methods"][-1]["method_type"] = verb.upper()

        # Consolidate results
        results = list(structure_map.values())
        if global_methods:
            results.append({
                "class_name": "Global",
                "class_type": "Utility",
                "base_path": "",
                "methods": global_methods,
                "file_name": file_name
            })
            
        return self.handle_extractor_output(results, file_path)