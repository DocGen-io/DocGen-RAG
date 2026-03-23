"""
AnalysisPipeline - Stage 2: AST-based controller extraction + code chunking.

Pipeline flow (parallel branches):
    files ──┬──→ ControllerExtractor ──→ endpoints
            └──→ ASTCodeSplitter     ──→ code_chunks

Replaces the previous LLM-based FilesAnalyzer bottleneck with fast,
deterministic AST extraction.
"""

from typing import List, Dict, Any

from haystack.core.pipeline import AsyncPipeline

from src.components.extractor.controller_extractor import ControllerExtractor
from src.components.ast_code_splitter import ASTCodeSplitter
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


class AnalysisPipeline:
    """Runs AST-based endpoint extraction and code chunking on changed files."""

    def __init__(self):
        self.pipeline = AsyncPipeline()
        self._build()

    def _build(self):
        self.pipeline.add_component("controller_extractor", ControllerExtractor())
        self.pipeline.add_component("code_splitter", ASTCodeSplitter())

    def run(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze changed files via AST extraction.

        Args:
            files: List of file dicts from IngestionPipeline.

        Returns:
            endpoints: flat list of endpoint dicts
            code_chunks: list of Haystack Document objects
        """
        if not files:
            logger.info("AnalysisPipeline: no changed files, skipping", location="run")
            return {"endpoints": [], "code_chunks": []}

        logger.info(f"AnalysisPipeline: analyzing {len(files)} file(s)", location="run")

        result = self.pipeline.run(
            {
                "controller_extractor": {"files": files},
                "code_splitter": {"files": files},
            },
            include_outputs_from={"controller_extractor", "code_splitter"},
        )

        extractor_out = result.get("controller_extractor", {})
        splitter_out = result.get("code_splitter", {})

        endpoints = extractor_out.get("endpoints", [])
        code_chunks = splitter_out.get("documents", [])

        logger.info(
            f"AnalysisPipeline: found {len(endpoints)} endpoints, {len(code_chunks)} code chunks",
            location="run",
        )

        return {
            "endpoints": endpoints,
            "code_chunks": code_chunks,
        }
