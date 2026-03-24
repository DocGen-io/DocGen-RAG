"""
EndpointClusterer - Groups API endpoints by semantic meaning using K-means.

Standalone component (not in main pipeline). Fetches endpoint doc embeddings
from Weaviate and clusters semantically similar endpoints together,
even if their URL paths differ (e.g. /payment and /user handling same kind of request).
"""

import math
from typing import Dict, Any, List, Optional

import numpy as np
from sklearn.cluster import KMeans
from haystack import component
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore

from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config

logger = DocGenLogger(__name__)


@component
class EndpointClusterer:
    """
    Clusters API endpoints by semantic similarity using K-means on embeddings.
    Not part of the main pipeline — called on demand.
    """

    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        config_path: str = "config.yaml"
    ):
        config = load_config(config_path)
        self.n_clusters = config.get("endpoint_clusterer", {}).get("n_clusters", "auto")
        self.weaviate_url = weaviate_url

    @staticmethod
    def _estimate_clusters(n_endpoints: int) -> int:
        """Estimate a reasonable cluster count using sqrt heuristic."""
        if n_endpoints <= 1:
            return max(1, n_endpoints)
        return max(1, min(n_endpoints, int(math.sqrt(n_endpoints))))

    def _cluster(
        self,
        endpoints: List[Dict[str, Any]],
        embeddings: np.ndarray,
        n_clusters: int
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Run K-means on embeddings and group endpoints by cluster."""
        if len(endpoints) == 0:
            return {}

        n_clusters = min(n_clusters, len(endpoints))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        labels = kmeans.fit_predict(embeddings)

        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for idx, label in enumerate(labels):
            clusters.setdefault(int(label), []).append(endpoints[idx])

        return clusters

    @component.output_types(clusters=Dict[int, List[Dict[str, Any]]])
    def run(self, n_clusters: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch endpoint docs from Weaviate, extract embeddings, and cluster.

        Args:
            n_clusters: Number of clusters. If None, uses config or auto-estimate.

        Returns:
            Dictionary with 'clusters' mapping cluster_id -> endpoint list.
        """
        # Fetch all endpoint documentation docs
        from src.utils.weaviate_utils import get_weaviate_store
        
        with get_weaviate_store(url=self.weaviate_url) as doc_store:
            docs = doc_store.filter_documents(
                filters={"field": "meta.doc_type", "operator": "==", "value": "endpoint_documentation"}
            )

        if not docs:
            logger.warning("No endpoint docs found in Weaviate")
            return {"clusters": {}}

        endpoints = []
        embeddings = []
        for doc in docs:
            if doc.embedding is not None:
                endpoints.append({
                    "name": doc.meta.get("endpoint_name", ""),
                    "path": doc.meta.get("path", ""),
                    "method": doc.meta.get("method", ""),
                    "summary": doc.meta.get("summary", ""),
                })
                embeddings.append(doc.embedding)

        if not embeddings:
            logger.warning("No embeddings found in endpoint docs")
            return {"clusters": {}}

        embeddings_array = np.array(embeddings)

        k = n_clusters or (
            self.n_clusters if isinstance(self.n_clusters, int)
            else self._estimate_clusters(len(endpoints))
        )

        clusters = self._cluster(endpoints, embeddings_array, n_clusters=k)
        logger.info(f"Clustered {len(endpoints)} endpoints into {len(clusters)} groups")
        return {"clusters": clusters}
