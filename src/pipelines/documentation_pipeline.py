"""
DocumentationPipeline - Orchestrator for the full documentation generation flow.

Calls three sub-pipelines in sequence:
    1. IngestionPipeline  — fetch sources, filter to changed files
    2. AnalysisPipeline   — AST/LLM analysis (bottleneck)
    3. IndexingPipeline   — write to Weaviate, generate & merge docs, save hashes

External interface (run() signature) is unchanged so src/api/main.py needs no edits.
"""

import os
import traceback
from typing import Dict, Any, Optional
import sys

import phoenix as px
from openinference.instrumentation.haystack import HaystackInstrumentor
from phoenix.otel import register

from src.pipelines.ingestion_pipeline import IngestionPipeline
from src.pipelines.analysis_pipeline import AnalysisPipeline
from src.pipelines.indexing_pipeline import IndexingPipeline
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


class DocumentationPipeline:
    """
    Orchestrates IngestionPipeline → AnalysisPipeline → IndexingPipeline.

    This class is the single entry-point for the API and CLI.
    """

    _instrumented = False

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.config_path = config_path
        self._setup_tracing()

        self.ingestion = IngestionPipeline()
        self.analysis = AnalysisPipeline()
        self.indexing = IndexingPipeline(config_path)

    def _setup_tracing(self):
        """Initialize Phoenix tracing if enabled in config."""
        if self.config.get("tracing") and not DocumentationPipeline._instrumented:
            try:
                tracer_provider = register(endpoint="http://127.0.0.1:6006/v1/traces")
                HaystackInstrumentor().instrument(tracer_provider=tracer_provider)
                DocumentationPipeline._instrumented = True
                logger.info("Phoenix tracing enabled", location="_setup_tracing")
            except Exception as e:
                logger.warning(f"Failed to setup Phoenix tracing: {e}", location="_setup_tracing")

    def run(
        self,
        source_type: str,
        path: str,
        credentials: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the full documentation generation pipeline.

        Args:
            source_type: "git" or "local"
            path: repository URL or local folder path
            credentials: optional git credentials

        Returns:
            Dictionary with pipeline metrics or error info
        """
        try:
            project_name = os.path.basename(os.path.normpath(path)).split("/")[-1]
            if project_name.endswith(".git"):
                project_name = project_name[:-4]
            if not project_name:
                project_name = "default_project"

            logger.info(f"Starting pipeline for '{project_name}' ({source_type}:{path})", location="run")

            # Stage 1: Ingest
            ingestion_out = self.ingestion.run(
                source_type=source_type,
                path=path,
                project_name=project_name,
                credentials=credentials,
            )
            files = ingestion_out["files"]
            pending_hashes = ingestion_out["pending_hashes"]

            if not files:
                logger.info("No changed files — pipeline complete (no-op)", location="run")
                return {"status": "completed", "files": 0, "message": "No changed files."}

            # Stage 2: Analyse
            analysis_out = self.analysis.run(files=files)
            analyzed_files = analysis_out["files"]

            # Stage 3: Index
            indexing_out = self.indexing.run(
                files=analyzed_files,
                pending_hashes=pending_hashes,
                project_name=project_name,
            )

            return {
                "status": "completed",
                "files": len(files),
                **indexing_out,
            }

        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg, location="run")
            return {
                "status": "failed",
                "error": str(e),
                "traceback": traceback.format_exc(),
            }


def main():
    """CLI entry-point: run pipeline on a local or git source."""

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
