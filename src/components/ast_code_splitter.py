"""
ASTCodeSplitter - Haystack component that uses GeneralExtractor (tree-sitter)
for structural, method-level code chunking.

Accepts raw file metadata from FileHasher and produces Haystack Documents
with metadata compatible with Weaviate storage and EndpointGraphManager lookups.

Deduplication: receives endpoint node_ids from ControllerExtractor and skips
any methods already captured as REST endpoints.
"""
import os
import hashlib
from haystack import component, Document
from typing import List, Dict, Any, Optional, Set

from src.components.extractor.general_extractor import GeneralExtractor
from src.utils.types import ASTOutputRecord
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

SUPPORTED_LANGUAGES = {"java", "c_sharp", "typescript"}


@component
class ASTCodeSplitter:
    """
    Haystack component that structurally chunks source code files using
    tree-sitter AST queries (GeneralExtractor) and outputs Haystack Documents
    ready for Weaviate storage.

    Each method/function extracted by the GeneralExtractor becomes one Document.
    Methods already captured by ControllerExtractor are skipped to avoid duplication.
    """

    def __init__(self):
        pass

    @component.output_types(documents=List[Document])
    def run(
        self,
        files: List[Dict[str, str]],
        endpoints: Optional[List[ASTOutputRecord]] = None,
    ) -> Dict[str, List[ASTOutputRecord]]:
        """
        Parse source files via GeneralExtractor and package each method
        as a Haystack Document.

        Args:
            files: List of file dicts from FileHasher (path, language, relative_path).
            endpoints: Optional list of ASTOutputRecord from ControllerExtractor.
                       Methods matching these node_ids are skipped.

        Returns:
            documents: List of Document objects with rich metadata for Weaviate.
        """
        # Build a set of node_ids already captured by ControllerExtractor
        endpoint_node_ids: Set[str] = set()
        if endpoints:
            for ep in endpoints:
                endpoint_node_ids.add(ep.node_id)

        split_docs: List[Document] = []

        for file_meta in files:
            file_path = file_meta.get("path", "")
            language = file_meta.get("language", "unknown")

            if language.lower() not in SUPPORTED_LANGUAGES:
                continue

            try:
                extractor = GeneralExtractor(language)
                records: List[ASTOutputRecord] = extractor.extract(file_path, file_meta)

                split_docs.extend([record for record in records if record.node_id not in endpoint_node_ids])

            except Exception as e:
                logger.error(f"GeneralExtractor failed for {file_path}: {e}")
                continue


        logger.info(
            f"ASTCodeSplitter produced {len(split_docs)} chunks from {len(files)} files"
            + (f" (skipped {len(endpoint_node_ids)} endpoint methods)" if endpoint_node_ids else ""),
            location="ASTCodeSplitter.run",
        )
        return {"documents": split_docs}
