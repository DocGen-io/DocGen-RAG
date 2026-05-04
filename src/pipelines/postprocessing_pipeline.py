"""
PostprocessingPipeline - On-demand grouping and fetch-example generation.

Two independent on-demand operations (NOT part of the main pipeline):
    - cluster()         : EndpointClusterer  — group all stored endpoint docs by semantics
    - fetch_example()   : FetchExampleGenerator — generate fetch code for a single endpoint
"""

import src.bootstrap
from typing import Dict, Any, Optional, List
from src.components.EndpointClusterer import EndpointClusterer
from src.components.FetchExampleGenerator import FetchExampleGenerator
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

from src.utils.weaviateStore import resolve_weaviate_url

logger = DocGenLogger(__name__)


class PostprocessingPipeline:
    """
    On-demand postprocessing.

    Each method is independent — call them individually as needed.
    """

    def __init__(self, config_path: str = "config.yaml"):
        config = load_config(config_path)
        weaviate_url = resolve_weaviate_url(config)

        self._clusterer = EndpointClusterer(weaviate_url=weaviate_url, config_path=config_path)
        self._example_gen = FetchExampleGenerator(config_path=config_path)

    def cluster(self, n_clusters: Optional[int] = None) -> Dict[int, List[Dict[str, Any]]]:
        """
        Group all stored endpoint docs by semantic similarity.

        Args:
            n_clusters: override cluster count. None = auto-estimate from config.

        Returns:
            { cluster_id: [endpoint_dict, ...] }
        """
        logger.info("PostprocessingPipeline: clustering endpoints", location="cluster")
        return self._clusterer.run(n_clusters=n_clusters).get("clusters", {})

    def fetch_example(self, swagger_data: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate fetch code examples for a single endpoint.

        Args:
            swagger_data: OpenAPI/Swagger dict for one endpoint (must include 'path').

        Returns:
            { "javascript": "...", "python": "...", "curl": "..." }
        """
        logger.info(
            f"PostprocessingPipeline: generating examples for {swagger_data.get('path', '?')}",
            location="fetch_example",
        )
        return self._example_gen.run(swagger_data=swagger_data).get("examples", {})
