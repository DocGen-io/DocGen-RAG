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
from src.utils.config_loader import load_config
 

logger = DocGenLogger(__name__)



@component
class ASTCodeSplitter:
    """
    Haystack component that structurally chunks source code files using
    tree-sitter AST queries (GeneralExtractor) and outputs Haystack Documents
    ready for Weaviate storage.

    Each method/function extracted by the GeneralExtractor becomes one Document.
    Methods already captured by ControllerExtractor are skipped to avoid duplication.
    """

    def __init__(self,config_path: str = "config.yaml"):
        self.config = load_config(config_path)

    @component.output_types(documents=List[Document])
    def run(
        self,
        files: List[Dict[str, str]],
        controller_files: Set[str],
    ) -> Dict[str, List[ASTOutputRecord]]:
        """
        Parse source files via GeneralExtractor and package each method
        as a Haystack Document.

        Args:
            files: List of file dicts from FileHasher (path, language, relative_path).
            controller_files: Set of file paths that are controllers used to skip chunking endpoints again.

        Returns:
            documents: List of Document objects with rich metadata for Weaviate.
        """
       

        for file_meta in files:
            file_path = file_meta.get("path", "")
            if file_path in controller_files:
                continue

            language = file_meta.get("language", "unknown")

            if language.lower() not in self.config.get("languages", []):
                continue

            try:
                extractor = GeneralExtractor(language)
                records: List[ASTOutputRecord] = extractor.extract(file_path, file_meta)


            except Exception as e:
                logger.error(f"GeneralExtractor failed for {file_path}: {e}")
                continue


        logger.info(
            f"ASTCodeSplitter produced {len(records)} chunks from {len(files)} files"
            + (f" (skipped {len(controller_files)} controller files)" if controller_files else ""),
            location="ASTCodeSplitter.run",
        )
        return {"documents": records, "finished": True}
