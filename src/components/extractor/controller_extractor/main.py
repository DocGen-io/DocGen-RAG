"""
ControllerExtractor - Haystack component for extracting REST API endpoints
using tree-sitter AST queries.

Uses the language-specific .scm queries from queries/controllers-extractors/
to precisely identify only REST endpoints (not gRPC, WebSocket, etc.).
"""
import os
from haystack import component
from typing import List, Dict, Any, Optional, Set

from tree_sitter import QueryCursor

from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
from src.utils.types import ASTOutputRecord
from src.utils.definitions import DECORATOR_TYPE_MAP
from src.components.extractor.base_extractor import BaseASTExtractor
from src.utils.weaviate_utils import get_node_id

from .strategies import get_strategy

logger = DocGenLogger(__name__)


class _ControllerQueryExtractor(BaseASTExtractor):
    """Internal extractor: parses one file using controller-specific queries."""

    def __init__(self, language_name: str):
        super().__init__(language_name)
        self.query_path = os.path.join(
            self.config["queries"]["controllers"],
            f"{language_name}.scm",
        )
        self.strategy = get_strategy(language_name)

    def extract(self, file_path: str, file_metadata: Optional[Dict[str, Any]] = None) -> List[ASTOutputRecord]:
        query = self._load_query(self.query_path)
        tree, code_bytes = self.parse_file(file_path)
        if not all([query, tree, code_bytes]):
            return []

        file_name = os.path.basename(file_path)
        rel_path = file_metadata["relative_path"] if file_metadata and "relative_path" in file_metadata else file_path

        controllers: Dict[str, Dict[str, Any]] = {}

        for _, captures in QueryCursor(query).matches(tree.root_node):
            
            class_name = self._get_capture_text(captures, "class_name", code_bytes, "Global")

            # Initialize controller if it's the first time we see this class
            if class_name not in controllers:
                controllers[class_name] = {
                    "class_name": class_name,
                    "base_path": "/",  # Default fallback
                    "methods": [],
                    "file_name": file_name,
                    "file_path": rel_path,
                    "node_id": get_node_id(file_name,class_name)
                }

            base_path = self.strategy.get_base_path(captures, self._get_capture_text, code_bytes, class_name)
            if base_path:
                controllers[class_name]["base_path"] = base_path

            method_def, method_name, raw_dec, decorator_path = self.strategy.get_endpoint_info(captures, self._get_capture_text, code_bytes, class_name)
            if not method_name or not method_def:
                continue

            decorator_type = DECORATOR_TYPE_MAP.get(raw_dec.lower())
            if not decorator_type:
                logger.warning(
                    f"Unknown decorator type for {class_name}.{method_name} in {file_name}",
                    location="_ControllerQueryExtractor.extract",
                )
                continue

            controllers[class_name]["methods"].append({
                "method_name": method_name,
                "method_definition": method_def,
                "method_type": decorator_type,
                "method_path": decorator_path,
                "is_api_route": True,
                "node_id": get_node_id(file_name,class_name,method_name)
            })

        # Remove any matched classes that had routes but NO actual HTTP endpoint methods
        valid_controllers = [c for c in controllers.values() if c["methods"]]

        if self.config.get("verbose"):
            logger.info(f"Extracted endpoints from {file_name}", location="_ControllerQueryExtractor.extract")

        return self.handle_extractor_output(valid_controllers, file_path)


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
        controller_files=Set[str],
        total_endpoints=int,
    )
    def run(self, files: List[Dict[str, str]],finished:bool=False) -> Dict[str, Any]:
        """Extract REST API endpoints from source files."""
        all_endpoints: List[ASTOutputRecord] = []
        controller_files: Set[str] = set()


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
                    controller_files.add(file_metadata.get('path',""))

            except Exception as e:
                logger.error(f"Error extracting controllers from {file_path}: {e}")

        logger.info(f"Extracted {len(all_endpoints)} endpoints from {len(controller_files)} controller file(s)")

        return {
            "endpoints": all_endpoints,
            "controller_files": controller_files,
            "total_endpoints": len(all_endpoints),
        }
