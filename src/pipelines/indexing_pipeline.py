"""
IndexingPipeline - Stage 3: Write code to Weaviate, generate docs, merge, vectorize, save hashes.

Pipeline flow:
    WeaviateCodeWriter + EndpointGraphManager -> DocumentationCreator
        -> DocumentationMerger + WeaviateDocWriter -> FileHashSaver

Only reached after AnalysisPipeline succeeds.
FileHashSaver commits hashes last, so a mid-run failure leaves no stale cache.
"""

from typing import List, Dict, Any

from haystack.core.pipeline import AsyncPipeline

from src.components.WeaviateCodeWriter import WeaviateCodeWriter
from src.components.EndpointGraphManager import EndpointGraphManager
from src.components.DocumentationCreator import DocumentationCreator
from src.components.DocumentationMerger import DocumentationMerger
from src.components.WeaviateDocWriter import WeaviateDocWriter
from src.components.FileHashSaver import FileHashSaver
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


class IndexingPipeline:
    """
    Writes analyzed code to Weaviate, generates & merges endpoint documentation,
    vectorizes docs, and finally commits file hashes on success.
    """

    def __init__(self, config_path: str = "config.yaml"):
        config = load_config(config_path)
        weaviate_url = config.get("WEAVIATE_URL") or "http://127.0.0.1:8080"

        self.pipeline = AsyncPipeline()
        self._build(weaviate_url, config_path)

    def _build(self, weaviate_url: str, config_path: str):
        self.pipeline.add_component("weaviate_writer", WeaviateCodeWriter(weaviate_url=weaviate_url))
        self.pipeline.add_component("graph_manager", EndpointGraphManager())
        self.pipeline.add_component(
            "doc_creator",
            DocumentationCreator(weaviate_url=weaviate_url, config_path=config_path),
        )
        self.pipeline.add_component("doc_merger", DocumentationMerger(config_path))
        self.pipeline.add_component(
            "weaviate_doc_writer",
            WeaviateDocWriter(weaviate_url=weaviate_url, config_path=config_path),
        )
        self.pipeline.add_component("file_hash_saver", FileHashSaver())

        # Weaviate code write (parallel with graph manager — both need files)
        self.pipeline.connect("weaviate_writer.documents_written", "graph_manager.documents_written")
        # Graph -> doc creator
        self.pipeline.connect("graph_manager.endpoint_graphs", "doc_creator.endpoint_graphs")
        # Doc creator -> merger
        self.pipeline.connect("doc_creator.output_dir", "doc_merger.output_dir")
        # Doc creator -> weaviate doc writer
        self.pipeline.connect("doc_creator.output_files", "weaviate_doc_writer.output_files")
        self.pipeline.connect("doc_creator.output_dir", "weaviate_doc_writer.output_dir")
        # Merger -> hash saver (commit only on success)
        self.pipeline.connect("doc_merger.endpoints_merged", "file_hash_saver.merge_status")

    def run(
        self,
        files: List[Dict[str, Any]],
        pending_hashes: Dict[str, str],
        project_name: str,
    ) -> Dict[str, Any]:
        """
        Index analyzed files into documentation.

        Args:
            files: analyzed file list from AnalysisPipeline
            pending_hashes: hash map from IngestionPipeline to commit if successful
            project_name: used for namespacing output dirs

        Returns:
            Summary metrics dict
        """
        if not files:
            logger.info("IndexingPipeline: no files to index, skipping", location="run")
            return {"documents_stored": 0, "endpoints_merged": 0, "hashes_saved": 0}

        logger.info(f"IndexingPipeline: indexing {len(files)} analyzed file(s)", location="run")

        result = self.pipeline.run(
            {
                "weaviate_writer": {"files": files},
                "graph_manager": {"project_name": project_name, "files": files},
                "doc_creator": {"project_name": project_name},
                "doc_merger": {"project_name": project_name},
                "file_hash_saver": {
                    "pending_hashes": pending_hashes,
                    "project_name": project_name,
                },
            },
            include_outputs_from={
                "weaviate_writer",
                "graph_manager",
                "doc_creator",
                "doc_merger",
                "file_hash_saver",
            },
        )

        writer_out = result.get("weaviate_writer", {})
        merger_out = result.get("doc_merger", {})
        creator_out = result.get("doc_creator", {})
        saver_out = result.get("file_hash_saver", {})

        return {
            "documents_stored": writer_out.get("documents_written", 0),
            "endpoint_graphs": len(result.get("graph_manager", {}).get("endpoint_graphs", {})),
            "methods_documented": creator_out.get("methods_processed", 0),
            "methods_failed": creator_out.get("methods_failed", 0),
            "endpoints_merged": merger_out.get("endpoints_merged", 0),
            "swagger_path": merger_out.get("swagger_path", ""),
            "hashes_saved": saver_out.get("hashes_saved", 0),
        }
