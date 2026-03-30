"""
QueryPipeline - Semantic + keyword search over stored endpoint documentation.

Given a natural-language prompt, embeds it and retrieves the top-k most relevant
endpoint docs from Weaviate using both:
  - Semantic search (vector similarity)
  - Keyword (BM25) search

Results are merged and deduplicated before returning.
"""

from typing import List, Dict, Any
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from haystack_integrations.components.retrievers.weaviate import (
    WeaviateEmbeddingRetriever,
    WeaviateBM25Retriever,
)
from src.utils.weaviate_utils import get_weaviate_store
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
import argparse
import json
logger = DocGenLogger(__name__)

# Filter: only endpoint documentation (not raw code chunks)
_ENDPOINT_DOC_FILTER = {
    "field": "meta.doc_type",
    "operator": "==",
    "value": "endpoint_documentation",
}


class QueryPipeline:
    """
    Retrieves the most relevant API endpoints from Weaviate for a user query.

    Uses both semantic (embedding) and keyword (BM25) retrieval then
    merges/deduplicates by endpoint path+method.
    """

    def __init__(self, config_path: str = "config.yaml"):
        config = load_config(config_path)
        weaviate_url = config.get("WEAVIATE_URL") or "http://127.0.0.1:8080"
        rag = config.get("rag", {})

        self.top_k = rag.get("top_k_retriever", 2)
        embedding_model = rag.get("embedding_model", "sentence-transformers/all-MiniLM-L6-v2")

        self.embedder = SentenceTransformersTextEmbedder(model=embedding_model)
        self.embedder.warm_up()
        self.weaviate_url = config.get("WEAVIATE_URL") or "http://127.0.0.1:8080"


    def run(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for API endpoints matching the given natural-language query.

        Args:
            query: Free-text description, e.g. "user authentication endpoint".

        Returns:
            List of endpoint dicts (path, method, summary, content) ordered by relevance.
        """

        with get_weaviate_store(url=self.weaviate_url) as doc_store:
            semantic_retriever = WeaviateEmbeddingRetriever(
                document_store=doc_store,
                top_k=self.top_k,
                # filters=_ENDPOINT_DOC_FILTER,
            )
            keyword_retriever = WeaviateBM25Retriever(
                document_store=doc_store,
                top_k=self.top_k,
                # filters=_ENDPOINT_DOC_FILTER,
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
                    "path": doc.meta.get("path", ""),
                    "method": doc.meta.get("method", ""),
                    "summary": doc.meta.get("summary", ""),
                    "content": doc.meta.get("raw_json") or doc.content or "Content not found!!",
                    "score": doc.score,
                })

        logger.info(f"QueryPipeline: returned {len(merged)} unique endpoints", location="run")
        return merged


def main():
    parser = argparse.ArgumentParser(description="Run query pipeline")
    parser.add_argument("--query", type=str, required=True, help="Query string")
    args = parser.parse_args()
    pipeline = QueryPipeline()
    results = pipeline.run(args.query)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()