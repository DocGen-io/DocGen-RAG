"""
WeaviateDocWriter - Haystack component to vectorize and store endpoint documentation in Weaviate.

Reads swagger.json files from DocumentationCreator output, embeds them,
and stores them in Weaviate for semantic search across API documentation.
"""

import json
import os
import hashlib
from typing import Dict, Any, List, Optional

from haystack import component, Document
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from src.utils.weaviate_utils import get_node_id
from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
from src.utils.weaviateStore import WeaviateStore, resolve_weaviate_url
from src.utils.rbac_utils import apply_rbac_metadata
from src.utils.pipeline_context import PipelineContext

logger = DocGenLogger(__name__)


@component
class WeaviateDocWriter:
    """
    Stores DocumentationCreator endpoint docs as vectorized documents in Weaviate.

    Enables semantic search across all API documentation
    (e.g. "give me all user-related endpoints").
    """

    def __init__(self, config_path: str = "config.yaml"):
        config = load_config(config_path)
        weaviate_url = resolve_weaviate_url(config)
        self.store = WeaviateStore.get_store(url=weaviate_url)
        embedding_model = config.get("rag", {}).get(
            "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.embedder = SentenceTransformersDocumentEmbedder(model=embedding_model)
        self.embedder.warm_up()
        self.ctx = PipelineContext()

    def _swagger_files_to_documents(
        self,
        output_files: Dict[str, Dict[str, str]],
    ) -> List[Document]:
        """Convert swagger output files to Haystack Documents for embedding."""
        documents = []

        for endpoint_name, files in output_files.items():
            swagger_path = files.get("swagger")
            if not swagger_path or not os.path.exists(swagger_path):
                logger.warning(f"No swagger.json for {endpoint_name}, skipping")
                continue

            try:
                with open(swagger_path, "r", encoding="utf-8") as f:
                    swagger_data = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read {swagger_path}: {e}")
                continue

            tags = swagger_data.get("tags", [])
            tag_str = ", ".join(tags) if isinstance(tags, list) else str(tags)
            path = swagger_data.get("path", "")
            method = swagger_data.get("method", "").upper()
            summary = swagger_data.get("summary", "")

            text_content = f"API Endpoint: {method} {path}. Tags: {tag_str}. Summary: {summary}".strip(" .")

            node_id = get_node_id(path, "API", method, api_details=self.ctx.to_dict())
            doc_id = hashlib.sha256(node_id.encode()).hexdigest()

            meta = {
                "endpoint_name": endpoint_name,
                "method": swagger_data.get("method", ""),
                "path": swagger_data.get("path", ""),
                "summary": swagger_data.get("summary", ""),
                "doc_type": "endpoint_documentation",
                "raw_json": json.dumps(swagger_data, indent=2),
                "node_id": node_id,
            }

            meta = apply_rbac_metadata(
                meta=meta,
                user_id=self.ctx.user_id,
                job_id=self.ctx.job_id,
                team_id=self.ctx.team_id,
                project_name=self.ctx.project_name,
            )

            meta = {k: v for k, v in meta.items() if v is not None}
            documents.append(Document(id=doc_id, content=text_content, meta=meta))

        return documents

    @component.output_types(documents_written=int)
    def run(
        self,
        output_files: Dict[str, Dict[str, str]],
        output_dir: str,
        project_name: Optional[str] = None,
        api_details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, int]:
        """
        Vectorize and store endpoint documentation in Weaviate.

        Args:
            output_files: Dict from DocumentationCreator (method_name -> file paths)
            output_dir: Output directory (unused, kept for pipeline wiring)
            project_name: Unique name for the project (updates ctx)
            api_details: Optional legacy dict (updates ctx for backward compat)
        """
        # Accept pipeline-level overrides for backward compatibility
        if project_name:
            self.ctx.project_name = project_name
        if api_details:
            self.ctx.user_id = self.ctx.user_id or api_details.get("user_id")
            self.ctx.team_id = self.ctx.team_id or api_details.get("team_id")
            self.ctx.job_id = self.ctx.job_id or api_details.get("job_id")

        if not output_files:
            logger.warning("No output files to vectorize")
            return {"documents_written": 0}

        documents = self._swagger_files_to_documents(output_files)

        if not documents:
            return {"documents_written": 0}

        # Embed documents
        embedded = self.embedder.run(documents=documents)
        embedded_docs = embedded.get("documents", documents)

        logger.info(f"Writing {len(embedded_docs)} documents to Weaviate...")

        writer = DocumentWriter(
            document_store=self.store,
            policy=DuplicatePolicy.OVERWRITE,
        )
        writer.run(documents=embedded_docs)

        logger.info(f"WeaviateDocWriter: stored {len(embedded_docs)} endpoint docs")
        return {"documents_written": len(embedded_docs)}
