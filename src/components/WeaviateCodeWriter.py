"""
WeaviateCodeWriter - Haystack component to store code data in Weaviate.

Handles two types of data:
1. AST-extracted endpoint definitions (from ControllerExtractor)
2. Structural code chunks (from ASTCodeSplitter)
"""

from haystack import component, Document
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from typing import List, Dict, Any, Optional
from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
import hashlib
import json
import os

logger = DocGenLogger(__name__)


@component
class WeaviateCodeWriter:
    """
    Haystack component that writes both endpoint definitions and code chunks
    to Weaviate for downstream dependency resolution and documentation generation.
    """

    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        additional_headers: Optional[Dict[str, str]] = None,
    ):
        self.weaviate_url = weaviate_url
        self.additional_headers = additional_headers or {}
        self.config = load_config("config.yaml")

        self.document_store = WeaviateDocumentStore(
            url=weaviate_url,
            additional_headers=self.additional_headers,
        )
        self.writer = DocumentWriter(
            document_store=self.document_store,
            policy=DuplicatePolicy.OVERWRITE,
        )

    # ------------------------------------------------------------------
    # Endpoint definitions → Documents
    # ------------------------------------------------------------------
    def endpoints_to_documents(self, endpoints: List[Dict[str, Any]]) -> List[Document]:
        """
        Convert ControllerExtractor endpoint dicts to Haystack Documents.

        Each endpoint becomes a single Document with:
          - content = method_definition
          - meta.type = "endpoint_definition"
          - meta.node_id = file_name:class_name:method_name
        """
        documents = []
        for ep in endpoints:
            node_id = ep.get("node_id") or f"{ep.get('file_name', 'unknown')}:{ep.get('class_name', 'Global')}:{ep.get('method_name', 'unknown')}:{ep.get('method_type', 'unknown')}"
            doc_id = hashlib.sha256(node_id.encode()).hexdigest()

            meta = {
                "type": "endpoint_definition",
                "node_id": node_id,
                "name": ep.get("method_name", ""),
                "class_name": ep.get("class_name", ""),
                "file_path": ep.get("file_path", ""),
                "file_name": ep.get("file_name", ""),
                "base_path": ep.get("base_path", "/"),
                "decorator_type": ep.get("decorator_type", ""),
                "decorator_path": ep.get("decorator_path", ""),
                "is_api_method": True,
                "api_method_details": json.dumps({
                    "method_type": ep.get("decorator_type", "GET"),
                    "path": ep.get("decorator_path", ""),
                    "base_path": ep.get("base_path", "/"),
                }),
            }
            meta = {k: v for k, v in meta.items() if v is not None}

            documents.append(Document(id=doc_id, content=ep.get("method_definition", ""), meta=meta))

        logger.info(f"Created {len(documents)} endpoint documents")
        return documents

    # ------------------------------------------------------------------
    # Code chunks → Documents  (from ASTCodeSplitter, already Documents)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Legacy: FilesAnalyzer output → Documents (kept for backward compat)
    # ------------------------------------------------------------------
    def analyzed_files_to_documents(self, analyzed_files: List[Dict[str, Any]]) -> List[Document]:
        """Convert FilesAnalyzer output to Haystack Documents (legacy path)."""
        documents = []
        for file_entry in analyzed_files:
            filename = file_entry.get("file_path", "unknown")
            items = file_entry.get("content", [])
            for item in items:
                documents.append(self._create_document_from_item(item, filename))
        logger.info(f"Created {len(documents)} documents from analyzed files")
        return documents

    def _create_document_from_item(self, item: Dict[str, Any], default_file_path: str) -> Document:
        lines = item.get("lines", [])
        content_str = "".join(lines) if isinstance(lines, list) else str(lines)

        is_api_method = item.get("is_api_method")
        is_api_method_bool = bool(is_api_method)
        is_api_method_details = json.dumps(is_api_method) if isinstance(is_api_method, dict) else None

        raw_deps = item.get("dependencies", [])
        dependencies_val = [json.dumps(d) if isinstance(d, dict) else str(d) for d in raw_deps]

        file_name = os.path.basename(item.get("file_path", default_file_path))
        origin_str = item.get("class_name", item.get("type", ""))
        name_str = item.get("name", "")
        node_id = f"{file_name}:{origin_str}:{name_str}"
        doc_id = hashlib.sha256(node_id.encode()).hexdigest()

        meta = {
            "type": item.get("type", ""),
            "name": item.get("name", ""),
            "file_path": item.get("file_path", default_file_path),
            "node_id": node_id,
            "class_name": item.get("class_name", ""),
            "is_api_method": is_api_method_bool,
        }
        if is_api_method_details:
            meta["api_method_details"] = is_api_method_details
        if dependencies_val:
            meta["dependencies"] = dependencies_val
            meta["dependency_count"] = len(dependencies_val)
        if lines:
            meta["lines"] = json.dumps(lines)
        meta = {k: v for k, v in meta.items() if v is not None}

        return Document(id=doc_id, content=content_str, meta=meta)

    @component.output_types(documents_written=int)
    def run(
        self,
        endpoints: Optional[List[Dict[str, Any]]] = None,
        code_chunks: Optional[List[Document]] = None,
        files: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, int]:
        """
        Write endpoint definitions and/or code chunks to Weaviate.

        Args:
            endpoints: endpoint dicts from ControllerExtractor
            code_chunks: Document list from ASTCodeSplitter
            files: legacy FilesAnalyzer output (backward compatibility)
        """
        logger.info("Starting WeaviateCodeWriter")
        all_documents: List[Document] = []

        # New AST-based path
        if endpoints:
            all_documents.extend(self.endpoints_to_documents(endpoints))
        if code_chunks:
            all_documents.extend(code_chunks)

        # Legacy path
        if files:
            all_documents.extend(self.analyzed_files_to_documents(files))

        if not all_documents:
            logger.warning("No documents created to write")
            return {"documents_written": 0}

        logger.info(f"Writing {len(all_documents)} documents to Weaviate...")
        self.writer.run(documents=all_documents)

        logger.info(f"Successfully wrote {len(all_documents)} documents to Weaviate")
        return {"documents_written": len(all_documents)}
