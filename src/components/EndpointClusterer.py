"""
EndpointClusterer - Groups API endpoints by semantic meaning using K-means.

Standalone component (not in main pipeline). Fetches endpoint doc embeddings
from Weaviate and clusters semantically similar endpoints together,
even if their URL paths differ (e.g. /payment and /user handling same kind of request).
"""

import math
import json
from typing import Dict, Any, List, Optional
import numpy as np
from sklearn.cluster import KMeans
from haystack import component
from haystack.dataclasses import ChatMessage
from sklearn.metrics import davies_bouldin_score
from src.utils.config_loader import load_config
from src.utils.weaviateStore import WeaviateStore
from src.utils.weaviate_utils import get_node_id
from src.utils.logger import DocGenLogger
from src.utils.model_generator import ModelGenerator
from src.utils.llm_json_handler import LLMJsonHandler
from prompts.cluster_naming_prompt import cluster_naming_system_prompt, cluster_naming_user_prompt
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
        config_path: str = "config.yaml"
    ):
        self.config = load_config(config_path)
        weaviate_url = self.config.get("WEAVIATE_URL", "http://127.0.0.1:8080")
        self.store = WeaviateStore.get_store(url=weaviate_url)
        self.n_clusters = self.config.get("endpoint_clusterer", {}).get("n_clusters", "auto")
        
        # Initialize LLM for logical naming
        self.generator = ModelGenerator("doc_creator", config_path).get_generator()

    def _name_clusters(self, clusters: Dict[int, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Use LLM to generate descriptive names for each cluster."""
        named_clusters = {}
        
        for cid, endpoints in clusters.items():
            try:
                # Prepare endpoint list for prompt
                ep_list_str = "\n".join([
                    f"- {ep.get('method', 'get').upper()} {ep.get('path', '')}: {ep.get('summary', '')}"
                    for ep in endpoints
                ])
                
                user_msg = cluster_naming_user_prompt.substitute(endpoints_list=ep_list_str)
                prompt = [
                    ChatMessage.from_system(cluster_naming_system_prompt),
                    ChatMessage.from_user(user_msg)
                ]
                
                response = LLMJsonHandler.parse_with_retry(
                    generator=self.generator,
                    prompt=prompt,
                    max_retries=2
                )
                
                cluster_name = response.get("cluster_name", f"Group {cid + 1}")
                named_clusters[cluster_name] = endpoints
                logger.info(f"Cluster {cid} named: '{cluster_name}'")
                
            except Exception as e:
                logger.warning(f"Failed to name cluster {cid}: {e}. Using fallback.")
                named_clusters[f"Group {cid + 1}"] = endpoints
                
        return named_clusters

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
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        
        # Auto-determine best K using Davies-Bouldin Index if not explicitly provided
        if not n_clusters or n_clusters <= 0:
            best_k = max(1, min(n_samples, 2))
            best_score = float('inf')  # Lower is better for DB index
            best_labels = None
            
            if n_samples >= 3:
                # Allow a more aggressive ceiling to naturally split smaller data structures
                max_k = min(n_samples - 1, max(4, (n_samples // 2) + 2))
                for k in range(2, max_k + 1):
                    kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
                    labels = kmeans.fit_predict(embeddings)
                    
                    if len(set(labels)) > 1 and len(set(labels)) < n_samples:
                        score = davies_bouldin_score(embeddings, labels)
                        logger.info(f"Evaluated K={k}: Davies-Bouldin Score = {score:.4f} (lower is better)")
                        if score < best_score:
                            best_score = score
                            best_k = k
                            best_labels = labels
                
                logger.info(f"Auto-selected optimal cluster count: {best_k} (Davies-Bouldin Score: {best_score:.4f})")
            
            n_clusters = best_k
            labels = best_labels if best_labels is not None else ([0] * n_samples)
        else:
            n_val = int(n_clusters)
            if n_val <= 1:
                labels = [0] * n_samples
            else:
                kmeans = KMeans(n_clusters=n_val, random_state=42, n_init="auto")
                labels = kmeans.fit_predict(embeddings)

        for idx, label in enumerate(labels):
            clusters.setdefault(int(label), []).append(endpoints[idx])

        return clusters

    @component.output_types(clusters=Dict[str, List[str]], api_details=Optional[Dict[str, Any]])
    def run(self, n_clusters: Optional[int] = None, api_details: Optional[Dict[str, Any]] = None, wait_for_weaviate: Optional[int] = None) -> Dict[str, Any]:
        """
        Fetch endpoint docs from Weaviate, extract embeddings, and cluster.

        Args:
            n_clusters: Number of clusters. If None, uses config or auto-estimate.
            api_details: Optional project/team context for filtering.

        Returns:
            Dictionary with 'clusters' mapping logical_name -> list of "method path".
        """
        if not self.config.get("process_grouping_automatically", False):
            logger.info("Automatic grouping disabled in config. Skipping EndpointClusterer.")
            return {"clusters": None, "api_details": api_details}

        filters = {"field": "meta.doc_type", "operator": "==", "value": "endpoint_documentation"}
        
        # Add project level filtering if api_details are present
        if api_details:
            team_id = api_details.get("team_id")
            project_name = api_details.get("project_name")
            
            conditions = [{"field": "meta.doc_type", "operator": "==", "value": "endpoint_documentation"}]
            if team_id:
                conditions.append({"field": "meta.team_id", "operator": "==", "value": team_id})
            if project_name:
                conditions.append({"field": "meta.project_name", "operator": "==", "value": project_name})
            
            if len(conditions) > 1:
                filters = {
                    "operator": "AND",
                    "conditions": conditions
                }

        # Fetch all filtered endpoint documentation docs
        docs = self.store.filter_documents(filters=filters)

        if not docs:
            logger.warning("No endpoint docs found in Weaviate")
            return {"clusters": {}}

        endpoints = []
        embeddings = []
        seen_endpoints = set()

        for doc in docs:
            if doc.embedding is not None:
                method = doc.meta.get("method", "").lower()
                path = doc.meta.get("path", "")
                ep_key = (method, path)
                
                if ep_key in seen_endpoints:
                    continue
                seen_endpoints.add(ep_key)

                endpoints.append({
                    "name": doc.meta.get("endpoint_name", ""),
                    "path": path,
                    "method": method,
                    "summary": doc.meta.get("summary", ""),
                    "node_id": doc.meta.get("node_id") or get_node_id(doc.meta.get("file_name", ""), doc.meta.get("class_name", ""), path, api_details=api_details)
                })
                embeddings.append(doc.embedding)

        if not embeddings:
            logger.warning("No embeddings found in endpoint docs")
            return {"clusters": {}}

        embeddings_array = np.array(embeddings)

        k = n_clusters or (self.n_clusters if isinstance(self.n_clusters, int) else None)

        raw_clusters = self._cluster(endpoints, embeddings_array, n_clusters=k)
        
        # Name the clusters logically
        named_clusters = self._name_clusters(raw_clusters)
        
        # Simplify output to just identifiers: "method path"
        simplified_clusters = {}
        for name, cluster_endpoints in named_clusters.items():
            simplified_clusters[name] = [
                ep['node_id']
                for ep in cluster_endpoints
            ]
        
        logger.info(f"Clustered {len(endpoints)} endpoints into {len(named_clusters)} logical groups")
        return {
            "clusters": simplified_clusters,
            "api_details": api_details
        }


def main():
    parser = argparse.ArgumentParser(description="Cluster API endpoints")
    parser.add_argument("--n_clusters", type=int, default=None, help="Number of clusters")
    parser.add_argument("--config_path", type=str, default="config.yaml", help="Path to config file")
    args = parser.parse_args()

    clusterer = EndpointClusterer(config_path=args.config_path)
    results = clusterer.run(n_clusters=args.n_clusters)
    clusters = results.get("clusters", {})
    
    for name, endpoints in clusters.items():
        print(f"\nGroup: {name} ({len(endpoints)} endpoints)")
        for ep in endpoints:
            print(f"  - {ep['method'].upper()} {ep['path']} ({ep['summary']})")


if __name__ == "__main__":
    main()