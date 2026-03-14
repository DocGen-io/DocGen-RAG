"""
AnalysisPipeline - Stage 2: AST / LLM file analysis (bottleneck).

Pipeline flow:
    FilesAnalyzer (parallel threads internally)

Receives a list of changed files from IngestionPipeline and produces
structured analysis results per file used by IndexingPipeline.
"""

from typing import List, Dict, Any

from haystack.core.pipeline import AsyncPipeline

from src.components.FilesAnalyzer import FilesAnalyzer
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


class AnalysisPipeline:
    """Runs LLM-based file analysis on changed files."""

    def __init__(self):
        self.pipeline = AsyncPipeline()
        self._build()

    def _build(self):
        self.pipeline.add_component("files_analyzer", FilesAnalyzer())

    def run(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze changed files.

        Args:
            files: List of file dicts from IngestionPipeline.

        Returns:
            files: List of analyzed file dicts with code chunks / endpoint info.
        """
        if not files:
            logger.info("AnalysisPipeline: no changed files, skipping", location="run")
            return {"files": []}

        logger.info(f"AnalysisPipeline: analyzing {len(files)} file(s)", location="run")

        result = self.pipeline.run(
            {"files_analyzer": {"files": files}},
            include_outputs_from={"files_analyzer"},
        )

        return {"files": result.get("files_analyzer", {}).get("files", [])}
