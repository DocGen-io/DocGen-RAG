"""
AnalysisPipeline - Stage 2: AST-based controller extraction + code chunking + dependency analysis.

Pipeline flow (sequential):
    files → ControllerExtractor → endpoints
                                  └──→ ASTCodeSplitter (skips endpoint methods) → code_chunks
    files → FilesAnalyzer → file_analysis (dependency mappings)

ControllerExtractor runs first; its endpoints are passed to ASTCodeSplitter
so that methods already captured as REST endpoints are not duplicated.
FilesAnalyzer runs in parallel on the same files to extract dependency mappings.
"""

from typing import List, Dict, Any

from haystack.core.pipeline import AsyncPipeline

from src.components.extractor.controller_extractor import ControllerExtractor
from src.components.ast_code_splitter import ASTCodeSplitter
from src.components.FilesAnalyzer import FilesAnalyzer
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


class AnalysisPipeline:
    """Runs AST-based endpoint extraction, code chunking, and dependency analysis on changed files."""

    def __init__(self, config_path: str = "config.yaml"):
        self.pipeline = AsyncPipeline('AnalysisPipeline')
        self._build(config_path)

    def _build(self, config_path: str):
        self.pipeline.add_component("code_splitter", ASTCodeSplitter(config_path=config_path))
        self.pipeline.add_component("controller_extractor", ControllerExtractor(config_path=config_path))
        self.pipeline.add_component("files_analyzer", FilesAnalyzer(config_path=config_path))

        # Wire controller endpoints → code_splitter for deduplication
        self.pipeline.connect("controller_extractor.controller_files", "code_splitter.controller_files")

    def run(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze changed files via AST extraction and LLM dependency analysis.

        Args:
            files: List of file dicts from IngestionPipeline.

        Returns:
            endpoints: flat list of ASTOutputRecord instances
            code_chunks: list of Haystack Document objects
            file_analysis: list of dependency analysis results per file
        """
        if not files:
            logger.info("AnalysisPipeline: no changed files, skipping", location="run")
            return {"endpoints": [], "code_chunks": [], "file_analysis": []}

        logger.info(f"AnalysisPipeline: analyzing {len(files)} file(s)", location="run")

        result = self.pipeline.run(
            {
                "code_splitter": {"files": files},
                "controller_extractor": {"files": files},
                "files_analyzer": {"files": files},
            },
            include_outputs_from={"controller_extractor", "code_splitter", "files_analyzer"},
        )

        extractor_out = result.get("controller_extractor", {})
        splitter_out = result.get("code_splitter", {})
        analyzer_out = result.get("files_analyzer", {})

        endpoints = extractor_out.get("endpoints", [])
        code_chunks = splitter_out.get("documents", [])
        file_analysis = analyzer_out.get("files", [])

        logger.info(
            f"AnalysisPipeline: found {len(endpoints)} endpoints, {len(code_chunks)} code chunks, "
            f"{len(file_analysis)} file analyses",
            location="run",
        )

        return {
            "endpoints": endpoints,
            "code_chunks": code_chunks,
            "file_analysis": file_analysis,
        }
