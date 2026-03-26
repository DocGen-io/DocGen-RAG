import os
from typing import List, Dict, Any, Optional
from tree_sitter import QueryCursor, Node
from .base_extractor import BaseASTExtractor
from src.utils.weaviate_utils import get_node_id
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

class GeneralExtractor(BaseASTExtractor):
    """
    Unified AST extractor for TS, Python, Java, and C#.
    Extracts all classes, interfaces, records and their methods using
    language-specific general queries. Does NOT handle REST routing —
    that is the responsibility of ControllerQueryExtractor.
    """

    CONTAINER_TAGS = ["class_name", "interface_name", "record_name"]
    METHOD_TAGS = ["method_name", "method_call"]

    def __init__(self, language_name: str):
        super().__init__(language_name)
        self.query_path = os.path.join(self.config["queries"]["general"], f"{language_name}.scm")

    @staticmethod
    def _find_parent_container(node: Node, structure_map: Dict[int, Dict[str, Any]]) -> Optional[Dict]:
        """Walk up the AST to find the nearest parent container in the structure map."""
        curr = node.parent
        while curr:
            if curr.id in structure_map:
                return structure_map[curr.id]
            curr = curr.parent
        return None

    def extract(self, file_path: str, file_metadata: Optional[Dict[str, Any]] = None) -> List['ASTOutputRecord']:
        query = self._load_query(self.query_path)
        tree, code_bytes = self.parse_file(file_path)
        if not all([query, tree, code_bytes]):
            return []

        structure_map: Dict[int, Dict[str, Any]] = {}
        global_methods: List[Dict[str, Any]] = []
        file_name = os.path.basename(file_path)

        # Resolve relative path
        rel_path = file_path
        if file_metadata and "relative_path" in file_metadata:
            rel_path = file_metadata["relative_path"]
        else:
            try:
                rel_path = os.path.relpath(file_path, os.getcwd())
            except ValueError:
                pass

        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

        for _, captures in matches:
            # 1. Handle Containers (Classes, Interfaces, Records)
            for tag in self.CONTAINER_TAGS:
                if tag not in captures:
                    continue

                name = self._get_capture_text(captures, tag, code_bytes)

                # Find the body/declaration node to anchor this container
                body_node = captures.get(
                    tag.replace("_name", "_body"),
                    captures.get(tag.replace("_name", "_declaration"),
                    captures.get(tag.replace("_name", "_node"),
                    captures.get(tag.replace("_name", "_definition"),
                    captures.get(tag, [None]))))
                )[0]


                
                if not body_node or body_node.id in structure_map:
                    continue

                base_path = ""
                if "class_decorator_path" in captures:
                    base_path = self._get_capture_text(captures, "class_decorator_path", code_bytes).strip("'\"")


                structure_map[body_node.id] = {
                    "class_name": name,
                    "base_path": base_path,
                    "methods": [],
                    "file_name": file_name,
                    "file_path": rel_path,
                    "node_id":  get_node_id(file_name,name)
                }

            # 2. Handle Methods and Functions
            for tag in self.METHOD_TAGS:
                if tag not in captures:
                    continue

                m_name = self._get_capture_text(captures, tag, code_bytes)
                m_body = captures.get(
                    tag.replace("_name", "_body"),
                    captures.get("method_definition", [None])
                )[0]

                if not m_body:
                    continue

                parent = self._find_parent_container(m_body, structure_map)


                method_data = {
                    "method_name": m_name,
                    "method_type": None,
                    "is_api_route": False,
                    "method_path": None,
                    "method_definition": self._trim_code(self._get_text(m_body, code_bytes)),
                    "node_id": get_node_id(file_name, parent["class_name"] if parent else "Global", m_name)
                }

                if parent:
                    if not any(m["method_name"] == m_name for m in parent["methods"]):
                        parent["methods"].append(method_data)
                else:
                    global_methods.append(method_data)

        # Consolidate results
        results = list(structure_map.values())
        if global_methods:
            results.append({
                "class_name": "Global",
                "base_path": rel_path,
                "methods": global_methods,
                "file_name": file_name,
                "file_path": file_path,
            })

        return self.handle_extractor_output(results, file_path)