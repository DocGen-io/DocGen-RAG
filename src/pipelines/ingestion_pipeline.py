"""
IngestionPipeline - Stage 1: Source fetch + file hashing.

Pipeline flow:
    SourceHandler -> FileHasher

Returns only files that have changed (new or modified hashes),
along with pending_hashes that will be committed after successful indexing.
"""

from typing import Optional, Dict, Any

from haystack.core.pipeline import AsyncPipeline

from src.components.SourceHandler import SourceHandler
from src.components.FileHasher import FileHasher
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


class IngestionPipeline:
    """Fetches source files and filters to only changed ones via hashing."""

    def __init__(self):
        self.pipeline = AsyncPipeline()
        self._build()

    def _build(self):
        self.pipeline.add_component("source_handler", SourceHandler())
        self.pipeline.add_component("file_hasher", FileHasher())

        self.pipeline.connect("source_handler.files", "file_hasher.files")
        self.pipeline.connect("source_handler.working_dir", "file_hasher.working_dir")

    def run(
        self,
        source_type: str,
        path: str,
        project_name: str,
        credentials: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetch and hash source files.

        Returns:
            files: changed files ready for analysis
            pending_hashes: hashes to save after successful pipeline completion
            working_dir: resolved working directory
        """
        logger.info(f"IngestionPipeline: starting for {path}", location="run")

        result = self.pipeline.run(
            {
                "source_handler": {
                    "source_type": source_type,
                    "path": path,
                    "credentials": credentials,
                },
                "file_hasher": {"project_name": project_name},
            },
            include_outputs_from={"file_hasher"},
        )

        hasher_out = result.get("file_hasher", {})
        return {
            "files": hasher_out.get("files", []),
            "pending_hashes": hasher_out.get("pending_hashes", {}),
        }
