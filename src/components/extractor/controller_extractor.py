"""
ControllerExtractor - Haystack component for extracting REST API endpoints
using tree-sitter AST queries.

Uses the language-specific .scm queries from queries/controllers-extractors/
to precisely identify only REST endpoints (not gRPC, WebSocket, etc.).
"""
import os
import hashlib
from haystack import component
from typing import List, Dict, Any, Optional
import json
from src.components.LanguageFinder import LanguageFinder
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
from tree_sitter import QueryCursor

from .base_extractor import BaseASTExtractor

logger = DocGenLogger(__name__)


class ControllerQueryExtractor(BaseASTExtractor):
    """
    Extracts REST controller endpoints using controller-specific tree-sitter queries.
    Each match from the query represents a confirmed REST endpoint.
    """

    DECORATOR_TYPE_MAP = {
        # Java Spring
        "getmapping": "GET", "postmapping": "POST", "putmapping": "PUT",
        "deletemapping": "DELETE", "patchmapping": "PATCH",
        "requestmapping": "GET",  # default, overridden if method= is specified
        # C# ASP.NET
        "httpget": "GET", "httppost": "POST", "httpput": "PUT",
        "httpdelete": "DELETE", "httppatch": "PATCH", "httpoptions": "OPTIONS",
        "httphead": "HEAD",
        # TypeScript/NestJS — decorator_type captured directly as Get, Post, etc.
        "get": "GET", "post": "POST", "put": "PUT",
        "delete": "DELETE", "patch": "PATCH", "options": "OPTIONS",
        "head": "HEAD", "all": "ALL",
    }

    def __init__(self, language_name: str):
        super().__init__(language_name)
        self.query_path = os.path.join(
            self.config["queries"]["controllers"],
            f"{language_name}.scm"
        )

    def extract(self, file_path: str, file_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Extract REST endpoints from a single file using controller queries."""

        # get settings if ast should be saved
        save_ast = self.config.get("ast_extractor", {}).get("save_ast", False)
        
        query = self._load_query(self.query_path)
        tree, code_bytes = self.parse_file(file_path)
        if not all([query, tree, code_bytes]):
            return []

        cursor = QueryCursor(query)
        matches = cursor.matches(tree.root_node)

        file_name = os.path.basename(file_path)
        rel_path = file_path
        if file_metadata and "relative_path" in file_metadata:
            rel_path = file_metadata["relative_path"]

        # Collect controllers and their methods
        controllers = {}  # class_name -> controller_info
        endpoints = []

        for _, captures in matches:
            # Extract class-level info
            class_name = self._get_capture_text(captures, "class_name", code_bytes, "Global")
            class_decorator_path = self._get_capture_text(
                captures, "class_decorator_path", code_bytes, ""
            ).strip("'\"")

            # Extract method-level info
            method_name = self._get_capture_text(captures, "method_name", code_bytes)
            if not method_name:
                continue

            # Get method definition body
            method_def_text = self._get_capture_text(captures, "method_definition", code_bytes)
            if not method_def_text:
                continue
            method_def_text = self._trim_code(method_def_text)

            # Get decorator type (HTTP verb)
            raw_decorator_type = self._get_capture_text(
                captures, "decorator_type", code_bytes, ""
            )
            decorator_type = self.DECORATOR_TYPE_MAP.get(
                raw_decorator_type.lower()
            )

            if not decorator_type:
                logger.warning(
                    f"Could not determine decorator type for method {method_name} in file {file_name} and class {class_name}",
                    location="ControllerQueryExtractor.extract",
                )
                continue

            # Get decorator path (method-level route)
            decorator_path = self._get_capture_text(
                captures, "decorator_path", code_bytes, ""
            ).strip("'\"")

            # Build the endpoint record
            node_id = f"{file_name}:{class_name}:{method_name}"
            endpoint = {
                "class_name": class_name,
                "method_name": method_name,
                "base_path": class_decorator_path or "/",
                "decorator_type": decorator_type,
                "decorator_path": decorator_path,
                "method_definition": method_def_text,
                "file_name": file_name,
                "file_path": rel_path,
                "node_id": node_id,
                "is_api_route": True,
                "method_type": decorator_type,
                "method_path": decorator_path,
            }

            if not any(
                e["class_name"] == class_name and e["decorator_path"] == decorator_path and e["decorator_type"] == decorator_type
                for e in endpoints
            ):
                endpoints.append(endpoint)
                if save_ast:
                    self.handle_extractor_output(endpoint, file_name)

        if self.config.get("verbose"):
            logger.info(
                f"Extracted {len(endpoints)} endpoints from {file_name}",
                location="ControllerQueryExtractor.extract",
            )
            

        return endpoints


@component
class ControllerExtractor:
    """
    Haystack component that extracts REST API endpoints from source files
    using AST-based tree-sitter queries.

    This replaces the LLM-based FilesAnalyzer for endpoint detection,
    providing precise, fast, and deterministic results.
    """

  

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.logger = DocGenLogger(self.__class__.__name__)

        
        self.SUPPORTED_LANGUAGES = self.config.get("languages", [])
        if not self.SUPPORTED_LANGUAGES:
            self.logger.error(
                "No languages found in config",
                location="ControllerExtractor.__init__",
            )
            raise ValueError("No languages found in config")

    def _extract_file(self, file_metadata: Dict[str, str]) -> List[Dict[str, Any]]:
        """Extract endpoints from a single file."""
        language = file_metadata.get("language", "unknown")
        if language not in self.SUPPORTED_LANGUAGES:
            return []

        try:
            extractor = ControllerQueryExtractor(language)
            return extractor.extract(file_metadata["path"], file_metadata)
        except Exception as e:
            self.logger.error(
                f"Error extracting controllers from {file_metadata.get('path')}: {e}",
                location="ControllerExtractor._extract_file",
            )
            return []

    @component.output_types(
        endpoints=List[Dict[str, Any]],
        controller_files=int,
        total_endpoints=int,
    )
    def run(self, files: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Extract REST API endpoints from source files.

        Args:
            files: List of file dicts from FileHasher (with path, language, relative_path)

        Returns:
            endpoints: flat list of endpoint dicts
            controller_files: number of files that contained controllers
            total_endpoints: total endpoints found
        """
        all_endpoints = []
        controller_files = 0

        for file_metadata in files:
            file_path = file_metadata.get("path", "")
            if not os.path.exists(file_path):
                self.logger.warning(
                    f"File not found: {file_path}",
                    location="ControllerExtractor.run",
                )
                continue

            endpoints = self._extract_file(file_metadata)
            if endpoints:
                all_endpoints.extend(endpoints)
                controller_files += 1

        self.logger.info(
            f"Extracted {len(all_endpoints)} endpoints from {controller_files} controller file(s)",
            location="ControllerExtractor.run",
        )

        return {
            "endpoints": all_endpoints,
            "controller_files": controller_files,
            "total_endpoints": len(all_endpoints),
        }
