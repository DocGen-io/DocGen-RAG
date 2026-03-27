"""
ControllerExtractor - Haystack component for extracting REST API endpoints
using tree-sitter AST queries.

Uses the language-specific .scm queries from queries/controllers-extractors/
to precisely identify only REST endpoints (not gRPC, WebSocket, etc.).
"""
import os
from haystack import component
from typing import List, Dict, Any, Optional

from tree_sitter import QueryCursor

from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
from src.utils.types import ASTOutputRecord
from src.utils.definitions import DECORATOR_TYPE_MAP
from .base_extractor import BaseASTExtractor
from src.utils.weaviate_utils import get_node_id
logger = DocGenLogger(__name__)


class _ControllerQueryExtractor(BaseASTExtractor):
    """Internal extractor: parses one file using controller-specific queries."""

    def __init__(self, language_name: str):
        super().__init__(language_name)
        self.query_path = os.path.join(
            self.config["queries"]["controllers"],
            f"{language_name}.scm",
        )

    def _resolve_method_name(self, captures: Dict[str, Any], code_bytes: bytes) -> Optional[str]:
        # 1. Try to get explicit method name (NestJS, Spring, etc.)
        method_name = self._get_capture_text(captures, "method_name", code_bytes)
        if method_name:
            return method_name

        # 2. Fallback for anonymous routes (Express, Flask, Fiber, etc.)
        raw_dec = self._get_capture_text(captures, "decorator_type", code_bytes, "")
        dec_path = self._get_capture_text(captures, "decorator_path", code_bytes, "").strip("'\"")
        
        if raw_dec and dec_path:
            clean_path = dec_path.replace("/", "_").replace(":", "").replace("-", "_").replace("{", "").replace("}", "")
            method_name = f"{raw_dec.lower()}_{clean_path}".strip("_")
            return method_name if method_name else f"{raw_dec.lower()}_handler"

        return None

    def extract(self, file_path: str, file_metadata: Optional[Dict[str, Any]] = None) -> List[ASTOutputRecord]:
        query = self._load_query(self.query_path)
        tree, code_bytes = self.parse_file(file_path)
        if not all([query, tree, code_bytes]):
            return []

        file_name = os.path.basename(file_path)
        rel_path = file_metadata["relative_path"] if file_metadata and "relative_path" in file_metadata else file_path

        controllers: Dict[str, Dict[str, Any]] = {}
        seen_methods: set = set()

        for _, captures in QueryCursor(query).matches(tree.root_node):
            class_name = self._get_capture_text(captures, "class_name", code_bytes, "Global")
            base_path = self._get_capture_text(captures, "class_decorator_path", code_bytes, "").strip("'\"") or "/"

            method_def = self._get_capture_text(captures, "method_definition", code_bytes)
            method_name = self._resolve_method_name(captures, code_bytes)

            if not method_name or not method_def:
                continue

            raw_dec = self._get_capture_text(captures, "decorator_type", code_bytes, "")
            decorator_type = DECORATOR_TYPE_MAP.get(raw_dec.lower())
            if not decorator_type:
                logger.warning(
                    f"Unknown decorator type for {class_name}.{method_name} in {file_name}",
                    location="_ControllerQueryExtractor.extract",
                )
                continue

            decorator_path = self._get_capture_text(captures, "decorator_path", code_bytes, "").strip("'\"")

            dedup_key = (class_name, method_name, decorator_type)
            if dedup_key in seen_methods:
                continue
            seen_methods.add(dedup_key)

            if class_name not in controllers:
                controllers[class_name] = {
                    "class_name": class_name,
                    "base_path": base_path,
                    "methods": [],
                    "file_name": file_name,
                    "file_path": rel_path,
                    "node_id": get_node_id(file_name,class_name)
                }

            controllers[class_name]["methods"].append({
                "method_name": method_name,
                "method_definition": method_def,
                "method_type": decorator_type,
                "method_path": decorator_path,
                "is_api_route": True,
                "node_id": get_node_id(file_name,class_name,method_name,decorator_type)
            })

        if self.config.get("verbose"):
            logger.info(f"Extracted endpoints from {file_name}", location="_ControllerQueryExtractor.extract")

        return self.handle_extractor_output(list(controllers.values()), file_path)


@component
class ControllerExtractor:
    """Haystack component: routes files to _ControllerQueryExtractor by language."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.supported_languages = self.config.get("languages", [])
        if not self.supported_languages:
            raise ValueError("No languages found in config")
            

    @component.output_types(
        endpoints=List[ASTOutputRecord],
        controller_files=int,
        total_endpoints=int,
    )
    def run(self, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """Extract REST API endpoints from source files."""
        all_endpoints: List[ASTOutputRecord] = []
        controller_files = 0


        # one per language
        extractors = {}

        for file_metadata in files:
            file_path = file_metadata.get("path", "")
            language = file_metadata.get("language", "unknown")
            if not os.path.exists(file_path) or language not in self.supported_languages:
                continue
            try:
                if language not in extractors:
                    extractors[language] = _ControllerQueryExtractor(language)
                endpoints = extractors[language].extract(file_path, file_metadata)
                if endpoints:
                    all_endpoints.extend(endpoints)
                    controller_files += 1
            except Exception as e:
                logger.error(f"Error extracting controllers from {file_path}: {e}")

        logger.info(f"Extracted {len(all_endpoints)} endpoints from {controller_files} controller file(s)")

        return {
            "endpoints": all_endpoints,
            "controller_files": controller_files,
            "total_endpoints": len(all_endpoints),
        }
