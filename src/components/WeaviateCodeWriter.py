"""
WeaviateCodeWriter - Haystack component to store code data in Weaviate.

Handles two types of data:
1. AST-extracted endpoint definitions (from ControllerExtractor)
2. Structural code chunks (from ASTCodeSplitter)
"""

import os
import json
import hashlib
from haystack import component, Document
from src.utils.logger import DocGenLogger
from src.utils.types import ASTOutputRecord
from typing import List, Dict, Any, Optional
from src.utils.config_loader import load_config
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from src.utils.weaviate_utils import get_weaviate_store,get_node_id
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from src.utils.weaviateStore import WeaviateStore

logger = DocGenLogger(__name__)


@component
class WeaviateCodeWriter:
    """
    Haystack component that writes both endpoint definitions and code chunks
    to Weaviate for downstream dependency resolution and documentation generation.
    """

    def __init__(
        self,
        config_path: str = "config.yaml",
        api_details: Optional[Dict[str, Any]] = None,
        additional_headers: Optional[Dict[str, str]] = None,
    ):
        self.config = load_config(config_path)
        weaviate_url = self.config.get("WEAVIATE_URL", "http://127.0.0.1:8080")
        self.store = WeaviateStore.get_store(url=weaviate_url)
        self.additional_headers = additional_headers or {}
        self.api_details = api_details
 
    def ast_endpoints_to_documents(self, ast_output: List[ASTOutputRecord],file_type:str='endpoint') -> List[Document]:
        """
        Convert AST output dicts to Haystack Documents.
        """
        
        documents = []
        for ep in ast_output:
            node_id = get_node_id(ep.get('file_name'),ep.get('class_name'),ep.get('method_name'))
            doc_id = hashlib.sha256(node_id.encode()).hexdigest()

            if file_type =='endpoint':
                add_on_meta = {
                    "is_api_method":True,
                     "api_method_details": json.dumps({
                    "decorator_type": ep.get("decorator_type", "GET"),
                    "path": ep.get("decorator_path", ""),
                    "base_path": ep.get("base_path", "/"),
                }),

                }
            else:  # non-controller file
                add_on_meta = {
                    "is_api_method":False,
                    "api_method_details": None,
                }
            

            meta = {
                "type":file_type,
                "node_id": node_id,
                "name": ep.get("method_name", ""),
                "class_name": ep.get("class_name", ""),
                "file_path": ep.get("file_path", ""),
                "file_name": ep.get("file_name", ""),
                "base_path": ep.get("base_path", "/"),
                "decorator_type": ep.get("decorator_type", ""),
                "decorator_path": ep.get("decorator_path", ""),
                **add_on_meta
            }

            if self.api_details:
                meta["api_details"] = json.dumps(self.api_details)
            meta = {k: v for k, v in meta.items() if v is not None}

            documents.append(Document(id=doc_id, content=ep.get("method_definition", ""), meta=meta))

        logger.info(f"Created {len(documents)} endpoint documents")
        return documents

    # ------------------------------------------------------------------
    # Code chunks → Documents  (from ASTCodeSplitter, already Documents)
    # ------------------------------------------------------------------

    @component.output_types(documents=List[Document],documents_written=int)
    def run(
        self,
        endpoints: Optional[List[ASTOutputRecord]] = None,
        code_chunks: Optional[List[ASTOutputRecord]] = None,
    ) -> Dict[str, int]:
        """
        Write endpoint definitions and/or code chunks to Weaviate.

        Args:
            endpoints: endpoint dicts from ControllerExtractor
            code_chunks: Document list from ASTCodeSplitter
        """
        logger.info("Starting WeaviateCodeWriter")
        all_documents: List[Document] = []

        # New AST-based path
        all_documents.extend(self.ast_endpoints_to_documents(endpoints))
        all_documents.extend(self.ast_endpoints_to_documents(code_chunks,file_type='code_chunk'))


        if not all_documents:
            logger.warning("No documents created to write")
            return {"documents_written": 0}

        logger.info(f"Writing {len(all_documents)} documents to Weaviate...")
        
        writer = DocumentWriter(
            document_store=self.store,
            policy=DuplicatePolicy.OVERWRITE,
        )
        writer.run(documents=all_documents)

        logger.info(f"Successfully wrote {len(all_documents)} documents to Weaviate")
        return {"documents":all_documents,"documents_written": len(all_documents)}
