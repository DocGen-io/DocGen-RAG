"""
WeaviateCodeWriter - Haystack component to store code data in Weaviate.

Handles two types of data:
1. AST-extracted endpoint definitions (from ControllerExtractor)
2. Structural code chunks (from ASTCodeSplitter)
"""

import json
import hashlib
from haystack import component, Document
from src.utils.logger import DocGenLogger
from src.utils.types import ASTOutputRecord
from typing import List, Dict, Any, Optional
from src.utils.config_loader import load_config
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from src.utils.weaviate_utils import get_node_id
from src.utils.weaviateStore import WeaviateStore, resolve_weaviate_url
from src.utils.rbac_utils import apply_rbac_metadata
from src.utils.pipeline_context import PipelineContext


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
        ctx: Optional[PipelineContext] = None,
    ):
        self.config = load_config(config_path)
        weaviate_url = resolve_weaviate_url(self.config)
        self.store = WeaviateStore.get_store(url=weaviate_url)
        self.ctx = ctx or PipelineContext()

    def ast_endpoints_to_documents(self, ast_output: List[ASTOutputRecord], file_type: str = 'endpoint') -> List[Document]:
        """Convert AST output dicts to Haystack Documents."""
        documents = []
        for ep in ast_output:
            node_id = get_node_id(
                ep.get('file_name'), ep.get('class_name'), ep.get('method_name'),
                api_details=self.ctx.to_dict()
            )
            doc_id = hashlib.sha256(node_id.encode()).hexdigest()

            if file_type == 'endpoint':
                add_on_meta = {
                    "is_api_method": True,
                    "api_method_details": json.dumps({
                        "decorator_type": ep.get("decorator_type", "GET"),
                        "path": ep.get("decorator_path", ""),
                        "base_path": ep.get("base_path", "/"),
                    }),
                }
            else:
                add_on_meta = {
                    "is_api_method": False,
                    "api_method_details": None,
                }

            meta = {
                "type": file_type,
                "doc_type": "code",
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

            meta = apply_rbac_metadata(
                meta=meta,
                user_id=self.ctx.user_id,
                job_id=self.ctx.job_id,
                team_id=self.ctx.team_id,
                project_name=self.ctx.project_name,
            )
            meta = {k: v for k, v in meta.items() if v is not None}

            documents.append(Document(id=doc_id, content=ep.get("method_definition", ""), meta=meta))

        logger.info(f"Created {len(documents)} endpoint documents")
        return documents

    # ------------------------------------------------------------------
    # Code chunks → Documents  (from ASTCodeSplitter, already Documents)
    # ------------------------------------------------------------------

    @component.output_types(documents=List[Document], documents_written=int)
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

        all_documents.extend(self.ast_endpoints_to_documents(endpoints))
        all_documents.extend(self.ast_endpoints_to_documents(code_chunks, file_type='code_chunk'))

        if not all_documents:
            logger.warning("No documents created to write")
            return {"documents_written": 0}

        logger.info(f"Writing {len(all_documents)} code docs to Weaviate...")

        writer = DocumentWriter(
            document_store=self.store,
            policy=DuplicatePolicy.OVERWRITE,
        )
        writer.run(documents=all_documents)

        logger.info(f"Successfully wrote {len(all_documents)} documents to Weaviate")
        return {"documents": all_documents, "documents_written": len(all_documents)}
