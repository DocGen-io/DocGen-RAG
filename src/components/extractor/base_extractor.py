"""
BaseASTExtractor - Abstract base for tree-sitter based AST extraction.

Provides shared utilities: language loading, query caching, file parsing,
text extraction, and the final flattening into ASTOutputRecord.
"""
import re
import os
import json

from tree_sitter_language_pack import get_language
from tree_sitter import Language, Parser, Tree, Query
from typing import Tuple, Optional, List, Dict, Any

from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
from src.utils.types import ASTOutputRecord


class BaseASTExtractor:
    """Base class for language-specific AST extraction."""

    def __init__(self, language_name: str, config_path: str = "config.yaml"):
        self.language_name = language_name
        full_config = load_config(config_path)
        self.config = full_config["ast_extractor"]
        self.config["queries"] = full_config.get("queries", {})
        self.logger = DocGenLogger(self.__class__.__name__)
        self.language = self._load_language()
        self.parser = Parser(self.language) if self.language else None
        self.query_cache: Dict[str, Query] = {}

    # ---- Language & query loading ----

    def _load_language(self) -> Optional[Language]:
        names_to_try = [
            self.language_name,
            self.language_name.replace("_", ""),
            self.language_name.replace("sharp", "_sharp"),
        ]
        for name in names_to_try:
            try:
                lang = get_language(name)
                if lang:
                    return lang
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
            with open(query_path, "r", encoding="utf-8") as f:
                query_text = f.read()
            query = Query(self.language, query_text)
            self.query_cache[query_path] = query
            return query
        except Exception as e:
            self.logger.error(f"Error loading query {query_path}: {e}", location="_load_query")
            return None

    # ---- Parsing & text helpers ----

    def parse_file(self, file_path: str) -> Tuple[Optional[Tree], Optional[bytes]]:
        if not self.parser:
            return None, None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code_str = f.read()
            code_bytes = code_str.encode("utf-8")
            return self.parser.parse(code_bytes), code_bytes
        except Exception as e:
            self.logger.error(f"Error parsing {file_path}: {e}", location="parse_file")
            return None, None

    def _get_text(self, node, code_bytes: bytes) -> str:
        if not node:
            return ""
        return code_bytes[node.start_byte : node.end_byte].decode("utf-8")

    def _get_capture_text(self, captures: Dict, key: str, code_bytes: bytes, default: str = "") -> str:
        if key not in captures:
            return default
        text = self._get_text(captures[key][0], code_bytes)
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            return text[1:-1]
        return text

    @staticmethod
    def _trim_code(code: str) -> str:
        """Collapse 3+ consecutive newlines and strip whitespace."""
        if not code:
            return code
        return re.sub(r"\n{3,}", "\n\n", code).strip()

    # ---- Output handling ----

    def handle_extractor_output(self, chunks: List[Dict[str, Any]], file_path: str) -> List[ASTOutputRecord]:
        """Flatten nested class→methods dicts into a flat list of ASTOutputRecord."""
        file_name = os.path.basename(file_path)

        if self.config["verbose"]:
            self.logger.info(json.dumps(chunks, indent=2), location="handle_extractor_output")

        if self.config["save_ast"]:
            os.makedirs(self.config["save_ast_path"], exist_ok=True)
            if not chunks:
                self.logger.warning(f"No chunks found for {file_name}", location="handle_extractor_output")
                return []
            save_name = f"{file_name}.json"
            with open(os.path.join(self.config["save_ast_path"], save_name), "w") as f:
                json.dump(chunks, f, indent=2)
            self.logger.info(f"Saved AST to {os.path.join(self.config['save_ast_path'], save_name)}", location="handle_extractor_output")

        records: List[ASTOutputRecord] = []
        for class_info in chunks:
            class_name = class_info.get("class_name", "Global")
            base_path = class_info.get("base_path", "")
            fp = class_info.get("file_path", file_path)

            for method in class_info.get("methods", []):
                method_name = method.get("method_name", "")
                method_type = method.get("method_type") or "unknown"
                method_path = method.get("method_path") or ""
                definition = self._trim_code(method.get("method_definition", ""))
                node_id = f"{file_name}:{class_name}:{method_name}:{method_type}"
                records.append(ASTOutputRecord(
                    class_name=class_name,
                    method_name=method_name,
                    base_path=base_path,
                    decorator_type=method_type,
                    decorator_path=method_path,
                    method_definition=definition,
                    file_name=file_name,
                    file_path=fp,
                    node_id=node_id,
                    is_api_route=method.get("is_api_route", False),
                    method_type=method_type,
                    method_path=method_path,
                ))

        return records

    def extract(self, file_path: str, file_metadata: Optional[Dict[str, Any]] = None) -> List[ASTOutputRecord]:
        raise NotImplementedError
