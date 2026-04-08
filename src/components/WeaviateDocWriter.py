"""
WeaviateDocWriter - Haystack component to vectorize and store endpoint documentation in Weaviate.

Reads swagger.json files from DocumentationCreator output, embeds them,
and stores them in Weaviate for semantic search across API documentation.
"""

import json
import os
from typing import Dict, Any, List, Optional

from haystack import component, Document
from haystack.components.writers import DocumentWriter
from haystack.components.embedders import SentenceTransformersDocumentEmbedder
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from src.utils.weaviate_utils import get_weaviate_store
from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config

logger = DocGenLogger(__name__)


@component
class WeaviateDocWriter:
    """
    Stores DocumentationCreator endpoint docs as vectorized documents in Weaviate.

    Enables semantic search across all API documentation
    (e.g. "give me all user-related endpoints").
    """

    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        config_path: str = "config.yaml",
        api_details: Optional[Dict[str, Any]] = None,
    ):
        config = load_config(config_path)
        embedding_model = config.get("rag", {}).get(
            "embedding_model", "sentence-transformers/all-MiniLM-L6-v2"
        )

        self.api_details = api_details
        self.weaviate_url = weaviate_url
        self.embedder = SentenceTransformersDocumentEmbedder(model=embedding_model)
        self.embedder.warm_up()

    def _swagger_files_to_documents(
        self, output_files: Dict[str, Dict[str, str]]
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

            doc = Document(
                content=text_content,
                meta={
                    "endpoint_name": endpoint_name,
                    "method": swagger_data.get("method", ""),
                    "path": swagger_data.get("path", ""),
                    "summary": swagger_data.get("summary", ""),
                    "doc_type": "endpoint_documentation",
                    "raw_json": json.dumps(swagger_data, indent=2),
                }
            )
            if self.api_details:
                doc.meta["api_details"] = json.dumps(self.api_details)
            documents.append(doc)

        return documents

    @component.output_types(documents_written=int)
    def run(
        self,
        output_files: Dict[str, Dict[str, str]],
        output_dir: str
    ) -> Dict[str, int]:
        """
        Vectorize and store endpoint documentation in Weaviate.

        Args:
            output_files: Dict from DocumentationCreator (method_name -> file paths)
            output_dir: Output directory (unused, kept for pipeline wiring)

        Returns:
            Dictionary with count of documents written
        """
        if not output_files:
            logger.warning("No output files to vectorize")
            return {"documents_written": 0}

        documents = self._swagger_files_to_documents(output_files)

        if not documents:
            return {"documents_written": 0}

        # Embed documents
        embedded = self.embedder.run(documents=documents)
        embedded_docs = embedded.get("documents", documents)


        # Write to Weaviate
        with get_weaviate_store(url=self.weaviate_url) as doc_store:
            doc_writer = DocumentWriter(document_store=doc_store)
            doc_writer.run(documents=embedded_docs)

        logger.info(f"WeaviateDocWriter: stored {len(embedded_docs)} endpoint docs")
        return {"documents_written": len(embedded_docs)}
