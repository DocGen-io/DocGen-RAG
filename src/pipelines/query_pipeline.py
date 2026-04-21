"""
QueryPipeline - Semantic + keyword search over stored endpoint documentation.

Given a natural-language prompt, embeds it and retrieves the top-k most relevant
endpoint docs from Weaviate using both:
  - Semantic search (vector similarity)
  - Keyword (BM25) search

Results are merged and deduplicated before returning.
"""
import os
import hashlib
import json
import argparse
from typing import List, Dict, Any, Optional

import src.bootstrap
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from haystack_integrations.components.retrievers.weaviate import (
    WeaviateEmbeddingRetriever,
    WeaviateBM25Retriever,
)
from src.utils.weaviate_utils import get_weaviate_store
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
from src.utils.weaviateStore import WeaviateStore
from src.utils.rbac_utils import build_rbac_filters
from src.utils.weaviateStore import resolve_weaviate_url
from src.components.embedders import EmbedderFactory

logger = DocGenLogger(__name__)

class QueryPipeline:
    """
    Retrieves the most relevant API endpoints from Weaviate for a user query.

    Uses both semantic (embedding) and keyword (BM25) retrieval then
    merges/deduplicates by endpoint path+method.
    """

    def __init__(self, config_path: str = "config.yaml", project_name: str | None = None):
        self.config = load_config(config_path)
        rag = self.config.get("rag", {})

        self.top_k = rag.get("top_k_retriever", 2)
        self.project_name = project_name
        provider = EmbedderFactory.create(self.config)
        self.embedder = provider.get_text_embedder()
        self.weaviate_url = resolve_weaviate_url(self.config)
        self.store = WeaviateStore.get_store(url=self.weaviate_url)


    def run(
        self, 
        query: str, 
        user_id: Optional[str] = None, 
        job_id: Optional[str] = None, 
        team_id: Optional[str] = None, 
        project_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for API endpoints matching the given natural-language query.

        Args:
            query: Free-text description, e.g. "user authentication endpoint".
            user_id: Optional user ID filter
            job_id: Optional job ID filter
            team_id: Optional team ID filter
            project_id: Optional project ID filter

        Returns:
            List of endpoint dicts (path, method, summary, content) ordered by relevance.
        """

        filters = build_rbac_filters(
            user_id=user_id,
            job_id=job_id,
            team_id=team_id,
            project_name=project_name or self.project_name,
        )

        semantic_retriever = WeaviateEmbeddingRetriever(
            document_store=self.store,
            top_k=self.top_k,
            filters=filters,
        )
        keyword_retriever = WeaviateBM25Retriever(
            document_store=self.store,
            top_k=self.top_k,
            filters=filters,
        )

        logger.info(f"QueryPipeline: querying for '{query}'", location="run")

        # Semantic retrieval
        embedding = self.embedder.run(text=query)["embedding"]
        semantic_docs = semantic_retriever.run(query_embedding=embedding).get("documents", [])

        # Keyword retrieval
        keyword_docs = keyword_retriever.run(query=query).get("documents", [])

        # Merge and deduplicate by (path, method)
        seen: set = set()
        merged: List[Dict[str, Any]] = []
        for doc in semantic_docs + keyword_docs:
            key = (doc.meta.get("path", ""), doc.meta.get("method", ""))
            if key not in seen:
                seen.add(key)
                merged.append({
                    "id": doc.id,
                    "path": doc.meta.get("path", ""),
                    "method": doc.meta.get("method", ""),
                    "summary": doc.meta.get("summary", ""),
                    "score": doc.score,
                })

        logger.info(f"QueryPipeline: returned {len(merged)} unique endpoints", location="run")
        return merged


def main():
    parser = argparse.ArgumentParser(description="Run query pipeline")
    parser.add_argument("--query", type=str, required=True, help="Query string")
    parser.add_argument("--project_name", type=str, required=True, help="Project name")

    args = parser.parse_args()
    pipeline = QueryPipeline()
    results = pipeline.run(args.query, project_name=args.project_name)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()