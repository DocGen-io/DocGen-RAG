"""
WeaviateCodeWriter - Haystack component to store required code data in Weaviate.
"""

from haystack import component, Document
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from typing import List, Dict, Any, Optional
from src.utils.logger import DocGenLogger
from src.utils.json_loader import load_json_folder
from src.utils.config_loader import load_config
import hashlib
import json
import os

logger = DocGenLogger(__name__)


@component
class WeaviateCodeWriter:
    """
    Haystack component that writes FilesAnalyzer data to Weaviate.
    
    Usage:
        writer = WeaviateCodeWriter(weaviate_url="http://localhost:8080")
        result = writer.run(
            input_folder="./files_analyzer",
        )
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        additional_headers: Optional[Dict[str, str]] = None
    ):
        """
        Initialize the WeaviateCodeWriter component.
        
        Args:
            weaviate_url: URL of the Weaviate instance
            additional_headers: Optional headers for Weaviate (e.g., API keys)
        """
        self.weaviate_url = weaviate_url
        self.additional_headers = additional_headers or {}
        self.config = load_config('config.yaml')
        
        # Initialize document store
        self.document_store = WeaviateDocumentStore(
            url=weaviate_url,
            additional_headers=self.additional_headers
        )
        
        # Initialize writer — OVERWRITE so re-runs replace old docs, never accumulate
        self.writer = DocumentWriter(document_store=self.document_store, policy=DuplicatePolicy.OVERWRITE)
    
    def analyzed_files_to_documents(self, analyzed_files: List[Dict[str, Any]]) -> List[Document]:
        """
        Convert FilesAnalyzer output to Haystack Documents.
        
        Args:
            analyzed_files: Dictionary mapping file paths to analysis results
            
        Returns:
            List of Haystack Document objects
        """
        documents = []
        
        for file_entry in analyzed_files:
            filename = file_entry.get('file_path', 'unknown')
            items = file_entry.get('content', [])
            
            for item in items:
                documents.append(self._create_document_from_item(item, filename))
        
        logger.info(f"Created {len(documents)} documents from analyzed files")
        return documents

    def _create_document_from_item(self, item: Dict[str, Any], default_file_path: str) -> Document:
        lines = item.get('lines', [])
        content_str = "".join(lines) if isinstance(lines, list) else str(lines)

        is_api_method = item.get('is_api_method')
        is_api_method_bool = bool(is_api_method)
        is_api_method_details = json.dumps(is_api_method) if isinstance(is_api_method, dict) else None

        raw_deps = item.get('dependencies', [])
        dependencies_val = [json.dumps(d) if isinstance(d, dict) else str(d) for d in raw_deps]

        file_name = os.path.basename(item.get('file_path', default_file_path))
        origin_str = item.get('class_name', item.get('type', ''))
        name_str = item.get('name', '')
        node_id = f"{file_name}:{origin_str}:{name_str}"

        # Deterministic document ID based on node_id — ensures OVERWRITE replaces old docs
        doc_id = hashlib.sha256(node_id.encode()).hexdigest()

        meta = {
            'type': item.get('type', ''),
            'name': item.get('name', ''),
            'file_path': item.get('file_path', default_file_path),
            'node_id': node_id,
            'class_name': item.get('class_name', ''),
            'is_api_method': is_api_method_bool,
        }

        if is_api_method_details:
            meta['api_method_details'] = is_api_method_details

        if dependencies_val:
            meta['dependencies'] = dependencies_val
            meta['dependency_count'] = len(dependencies_val)

        if lines:
            meta['lines'] = json.dumps(lines)

        # Strip any None values to avoid polluting Weaviate schema with null fields
        meta = {k: v for k, v in meta.items() if v is not None}

        doc = Document(
            id=doc_id,
            content=content_str,
            meta=meta
        )
        return doc
    
    @component.output_types(
        documents_written=int,
    )
    def run(
        self,
        files: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """
        Process analyzer files output and write to Weaviate.
        
        Args:
            files: Dictionary of analyzed files from FilesAnalyzer.
            
        Returns:
            Dictionary with count of documents written
        """
        logger.info(f"Starting WeaviateCodeWriter")
        
        if not files:
            logger.warning("No files provided to write")
            
        # Process to documents
        documents = self.analyzed_files_to_documents(files)
        
        if not documents:
            logger.warning("No documents created to write")
            return {"documents_written": 0}
        
        # Write to Weaviate (no embedder)
        logger.info(f"Writing {len(documents)} documents to Weaviate without vectorization...")
        self.writer.run(documents=documents)
        
        result = {
            "documents_written": len(documents)
        }
        
        logger.info(f"Successfully wrote {result['documents_written']} documents to Weaviate")
        return result
