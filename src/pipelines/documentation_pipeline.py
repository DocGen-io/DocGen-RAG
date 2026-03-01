"""
Documentation Pipeline - Full pipeline for API documentation generation.

Pipeline Flow:
1. Input: SourceHandler
2. Validation: FrameworkValidator
3. Analysis: FilesAnalyzer
5. Storage: WeaviateCodeWriter
6. Generation: DocumentationCreator (LLM)
7. Finalizing: DocumentationMerger

With Arize Phoenix tracing enabled.
"""
import os
import logging
from typing import Dict, Any, Optional, List

from haystack import Pipeline
import phoenix as px
from openinference.instrumentation.haystack import HaystackInstrumentor
from phoenix.otel import register
import json

from src.components.SourceHandler import SourceHandler
from src.components.FrameworkValidator import FrameworkValidator
from src.components.WeaviateCodeWriter import WeaviateCodeWriter
from src.components.FileHasher import FileHasher
from src.components.DocumentationCreator import DocumentationCreator
from src.components.DocumentationMerger import DocumentationMerger
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
import traceback
from src.components.FilesAnalyzer import FilesAnalyzer
from src.components.EndpointGraphManager import EndpointGraphManager

logger = DocGenLogger(__name__)


class DocumentationPipeline:
    """
    Full documentation generation pipeline with Phoenix tracing.
    
    Uses a SINGLE Haystack Pipeline connecting all components:
    Source -> Validator -> AST -> CodeMapper -> Weaviate -> Creator -> Merger
    
    Data flows directly between components.
    """
    
    _instrumented = False
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.config_path = config_path
        self._setup_tracing()
        self.weaviate_url = self.config['WEAVIATE_URL'] or "http://127.0.0.1:8080"
        
        self.pipeline = Pipeline()
        self._build_pipeline()
    
    def _setup_tracing(self):
        """Initialize Phoenix tracing if enabled."""
        phoenix_enabled = self.config["tracing"] or False
        if phoenix_enabled and not DocumentationPipeline._instrumented:
            try:
                tracer_provider = register(endpoint="http://127.0.0.1:6006/v1/traces")
                HaystackInstrumentor().instrument(tracer_provider=tracer_provider)
                DocumentationPipeline._instrumented = True
                DocumentationPipeline._instrumented = True
                logger.info("Phoenix tracing enabled", location="_setup_tracing")
            except Exception as e:
                logger.warning(f"Failed to setup Phoenix tracing: {e}", location="_setup_tracing")

    def _build_pipeline(self):
        """Build the single unified pipeline."""
        # Initialize components
        source_handler = SourceHandler()
        # framework_validator = FrameworkValidator(self.config_path)

        weaviate_writer = WeaviateCodeWriter(weaviate_url=self.weaviate_url)
        doc_creator = DocumentationCreator(
            weaviate_url=self.weaviate_url,
            config_path=self.config_path
        )
        doc_merger = DocumentationMerger(self.config_path)
        file_hasher = FileHasher()
        files_analyzer = FilesAnalyzer()
        graph_manager = EndpointGraphManager()
        
        # Add components
        self.pipeline.add_component("source_handler", source_handler)
        self.pipeline.add_component("file_hasher", file_hasher)
        self.pipeline.add_component("files_analyzer", files_analyzer)
        self.pipeline.add_component("weaviate_writer", weaviate_writer)
        self.pipeline.add_component("graph_manager", graph_manager)
        self.pipeline.add_component("doc_creator", doc_creator)
        self.pipeline.add_component("doc_merger", doc_merger)

        # Connect components
        # 1. Source -> Hasher
        self.pipeline.connect("source_handler.files", "file_hasher.files")
        self.pipeline.connect("source_handler.working_dir", "file_hasher.working_dir")
        # 2. Hasher -> Analyzer
        self.pipeline.connect("file_hasher.files", "files_analyzer.files")
        # 3a. Analyzer -> GraphManager
        self.pipeline.connect("files_analyzer.files", "graph_manager.files")
        # 3b. Analyzer -> Weaviate
        self.pipeline.connect("files_analyzer.files", "weaviate_writer.files")
        # 4. GraphManager -> DocMaker
        self.pipeline.connect("graph_manager.endpoint_graphs", "doc_creator.endpoint_graphs")
        # 5. DocMaker -> DocMerger
        self.pipeline.connect("doc_creator.output_dir", "doc_merger.output_dir")
    
    def run(
        self,
        source_type: str,
        path: str,
        credentials: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the unified pipeline.
        
        Args:
            source_type: "git" or "local"
            path: Repository URL or local folder path
            credentials: Optional git credentials
            
        Returns:
            Dictionary with pipeline results
        """
        try:
            logger.info(f"Starting unified pipeline run for {path} ({source_type})", location="run")
            
            # Extract project name from path
            # E.g., from 'apis-test/nestjs' -> 'nestjs'
            # E.g., from 'https://github.com/user/repo.git' -> 'repo'
            project_name = os.path.basename(os.path.normpath(path))
            project_name = project_name.split("/")[-1]
            print(project_name)
            if project_name.endswith('.git'):
                project_name = project_name[:-4]
            if not project_name:
                project_name = "default_project"
            
            result = self.pipeline.run(
                {
                    "source_handler": {
                        "source_type": source_type,
                        "path": path,
                        "credentials": credentials
                    },
                    "file_hasher": {
                        "project_name": project_name
                    },
                    "graph_manager": {
                        "project_name": project_name
                    },
                    "doc_creator": {
                        "project_name": project_name
                    },
                    "doc_merger": {
                        "project_name": project_name
                    }
                },
                include_outputs_from={"files_analyzer", "weaviate_writer", "graph_manager", "doc_creator", "doc_merger"}
            )
            
            # Extract results for report
            files = result.get("files_analyzer", {}).get("files", {})
            
            
            writer_result = result.get("weaviate_writer", {})
            graph_result = result.get("graph_manager", {})
            merger_result = result.get("doc_merger", {})
            doc_creator_result = result.get("doc_creator", {})
            
            return {
                "status": "completed",
                "files": len(files),
                "documents_stored": writer_result.get("documents_written", 0),
                "endpoint_graphs": len(graph_result.get("endpoint_graphs", {})),
                "methods_documented": doc_creator_result.get("methods_processed", 0),
                "methods_failed": doc_creator_result.get("methods_failed", 0),
                "endpoints_merged": merger_result.get("endpoints_merged", 0),
                "swagger_path": merger_result.get("swagger_path", ""),
            }
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg, location="run")
            
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc()
            }


def main():
    """Run pipeline on apis-test directory for testing."""
    import sys
    
    source_type = "local"
    path = "apis-test/nestjs"
    
    if len(sys.argv) == 3:
        source_type = sys.argv[1]
        path = sys.argv[2]
    elif len(sys.argv) == 2:
        path = sys.argv[1]
        
    pipeline = DocumentationPipeline()
    result = pipeline.run(source_type=source_type, path=path)
    
    print("\n=== Pipeline Result ===")
    for key, value in result.items():
        if key != "traceback":
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
