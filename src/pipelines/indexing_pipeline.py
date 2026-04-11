"""
IndexingPipeline - Stage 3: Write to Weaviate, build graphs, generate & merge docs, save hashes.

Pipeline flow:
    WeaviateCodeWriter ──→ DocumentationCreator ──→ DocumentationMerger ──→ FileHashSaver
           ↑                        ↑                       ↑
    EndpointGraphManager ──────────┘

WeaviateCodeWriter receives endpoints + code chunks from AnalysisPipeline.
EndpointGraphManager builds dependency graphs from file_analysis (FilesAnalyzer output).
DocumentationCreator uses the graphs + Weaviate to generate docs.
"""

from typing import List, Dict, Any, Optional
from haystack import Document
from haystack.core.pipeline import AsyncPipeline

from src.components.WeaviateCodeWriter import WeaviateCodeWriter
from src.components.EndpointGraphManager import EndpointGraphManager
from src.components.DocumentationCreator import DocumentationCreator
from src.components.DocumentationMerger import DocumentationMerger
from src.components.WeaviateDocWriter import WeaviateDocWriter
from src.components.FileHashSaver import FileHashSaver
from src.utils.config_loader import load_config
from src.utils.types import ASTOutputRecord
from src.utils.logger import DocGenLogger


logger = DocGenLogger(__name__)


class IndexingPipeline:
    """
    Writes code data to Weaviate, builds endpoint dependency graphs,
    generates & merges documentation, and commits file hashes on success.
    """

    def __init__(self, config_path: str = "config.yaml",api_details: Optional[Dict[str, Any]] = None):
        config = load_config(config_path)
        weaviate_url = config.get("WEAVIATE_URL") or "http://127.0.0.1:8080"
        self.api_details = api_details
        self.pipeline = AsyncPipeline()
        self._build(config_path)
        self.api_details = api_details

            
    def _build(self, config_path: str):
        self.pipeline.add_component("weaviate_writer", WeaviateCodeWriter(config_path=config_path,api_details=self.api_details))
        self.pipeline.add_component("graph_manager", EndpointGraphManager())
        self.pipeline.add_component(
            "doc_creator",
            DocumentationCreator(config_path=config_path),
        )
        self.pipeline.add_component("doc_merger", DocumentationMerger(config_path=config_path))
        self.pipeline.add_component(
            "weaviate_doc_writer",
            WeaviateDocWriter(config_path=config_path),
        )
        self.pipeline.add_component("file_hash_saver", FileHashSaver())

        # Writer → doc creator
        self.pipeline.connect("weaviate_writer.documents_written", "doc_creator.wait_for_weaviate")
        # Graph → doc creator
        self.pipeline.connect("graph_manager.endpoint_graphs", "doc_creator.endpoint_graphs")
        # Doc creator → merger
        self.pipeline.connect("doc_creator.output_dir", "doc_merger.output_dir")
        # Doc creator → weaviate doc writer
        self.pipeline.connect("doc_creator.output_files", "weaviate_doc_writer.output_files")
        self.pipeline.connect("doc_creator.output_dir", "weaviate_doc_writer.output_dir")
        # Merger → hash saver (commit only on success)
        self.pipeline.connect("doc_merger.endpoints_merged", "file_hash_saver.merge_status")
        # Ensure merger waits for doc writer (ordering only)
        self.pipeline.connect("weaviate_doc_writer.documents_written", "doc_merger.wait_for_weaviate")

    def run(
        self,
        endpoints: List[ASTOutputRecord],
        code_chunks: List[ASTOutputRecord],
        file_analysis: List[Dict[str, Any]],
        pending_hashes: Dict[str, str],
        project_name: str,
        working_dir: str = "",
    ) -> Dict[str, Any]:
        """
        Index endpoints and code chunks into documentation.

        Args:
            endpoints: endpoint list from AnalysisPipeline (ControllerExtractor)
            code_chunks: Document list from AnalysisPipeline (ASTCodeSplitter)
            file_analysis: dependency analysis from AnalysisPipeline (FilesAnalyzer)
            pending_hashes: hash map from IngestionPipeline
            project_name: used for namespacing output dirs
            working_dir: resolved working directory
        """
        if not endpoints:
            logger.info("IndexingPipeline: no endpoints to index, skipping", location="run")
            return {"documents_stored": 0, "endpoints_merged": 0, "hashes_saved": 0}

        logger.info(
            f"IndexingPipeline: indexing {len(endpoints)} endpoint(s), {len(code_chunks)} chunk(s), "
            f"{len(file_analysis)} file analyses",
            location="run",
        )

        result = self.pipeline.run(
            {
                "weaviate_writer": {
                    "endpoints": endpoints,
                    "code_chunks": code_chunks,
                },
                "graph_manager": {
                    "project_name": project_name,
                    "files": file_analysis,
                    "endpoints": endpoints,
                },
                "doc_creator": {"project_name": project_name},
                "doc_merger": {
                    "project_name": project_name,
                    "api_details": self.api_details
                },
                "weaviate_doc_writer": {
                    "api_details": self.api_details
                },
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
            "swagger_spec": merger_out.get("swagger_spec", {}),
            "hashes_saved": saver_out.get("hashes_saved", 0),
        }
