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
from sklearn.metrics import davies_bouldin_score
from src.utils.weaviate_utils import get_weaviate_store
from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
import argparse
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

    def _cluster(
        self,
        endpoints: List[Dict[str, Any]],
        embeddings: np.ndarray,
        n_clusters: Optional[int] = None
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Run K-means on embeddings and group endpoints by cluster. Auto-estimates optimal K using Davies-Bouldin index."""
        if len(endpoints) == 0:
            return {}

        n_samples = len(endpoints)
        
        # Auto-determine best K using Davies-Bouldin Index if not explicitly provided
        if not n_clusters or n_clusters <= 0:
            best_k = max(1, min(n_samples, 2))
            best_score = float('inf')  # Lower is better for DB index
            kmeans_results = {}
            if n_samples >= 3:
                # Allow a more aggressive ceiling to naturally split smaller data structures
                max_k = min(n_samples - 1, max(4, (n_samples // 2) + 2))
                for k in range(2, max_k + 1):
                    kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
                    labels = kmeans.fit_predict(embeddings)
                    kmeans_results[k] = labels
                    if len(set(labels)) > 1 and len(set(labels)) < n_samples:
                        score = davies_bouldin_score(embeddings, labels)
                        logger.info(f"Evaluated K={k}: Davies-Bouldin Score = {score:.4f} (lower is better)")
                        if score < best_score:
                            best_score = score
                            best_k = k
                
                logger.info(f"Auto-selected optimal cluster count: {best_k} (Davies-Bouldin Score: {best_score:.4f})")
            n_clusters = best_k

        n_clusters = min(n_clusters, n_samples)
        
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        if n_clusters <= 1:
            labels = [0] * n_samples
        elif locals().get("kmeans_results") and locals().get("best_k") in locals().get("kmeans_results", {}):
            labels = locals()["kmeans_results"][locals()["best_k"]]
        else:
            # Fallback if a hardcoded 'n_clusters' skipped the 'auto' block
            kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
            labels = kmeans.fit_predict(embeddings)

        for idx, label in enumerate(labels):
            clusters.setdefault(int(label), []).append(endpoints[idx])

        # Log the clusters and their endpoints
        for cid, clist in clusters.items():
            ep_names = [ep.get("path", "unknown") for ep in clist]
            logger.info(f"Cluster {cid} contains ({len(clist)} endpoints): {', '.join(ep_names)}")

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

        k = n_clusters or (self.n_clusters if isinstance(self.n_clusters, int) else None)

        clusters = self._cluster(endpoints, embeddings_array, n_clusters=k)
        logger.info(f"Clustered {len(endpoints)} endpoints into {len(clusters)} groups")
        return {"clusters": clusters}


def main():
    parser = argparse.ArgumentParser(description="Cluster API endpoints")
    parser.add_argument("--n_clusters", type=int, default=None, help="Number of clusters")
    parser.add_argument("--config_path", type=str, default="config.yaml", help="Path to config file")
    parser.add_argument("--weaviate_url", type=str, default="http://127.0.0.1:8080", help="Weaviate URL")
    args = parser.parse_args()

    clusterer = EndpointClusterer(weaviate_url=args.weaviate_url, config_path=args.config_path)
    results = clusterer.run(n_clusters=args.n_clusters)
    clusters = results.get("clusters", {})
    logger.info(f"Clustered into {len(clusters)} groups")


if __name__ == "__main__":
    __main__()