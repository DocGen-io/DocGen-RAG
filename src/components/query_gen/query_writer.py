"""
QueryWriter — Saves validated .scm queries to the generated queries directory.

Output structure:
    queries/generated/<framework_name>/controllers-extractors/<language>.scm
    queries/generated/<framework_name>/general/<language>.scm
"""

import os
from typing import Dict, List, Optional

from haystack import component

from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


@component
class QueryWriter:
    """Persists validated .scm queries to the filesystem."""

    def __init__(self, config_path: str = "config.yaml"):
        config = load_config(config_path)
        self.generated_dir = config.get("queries", {}).get(
            "generated", "queries/generated"
        )

    @component.output_types(saved_paths=List[str])
    def run(
        self,
        queries: Dict[str, str],
        framework_name: str,
        language: str,
        mock_files: Optional[List[Dict[str, str]]] = None,
    ) -> Dict[str, List[str]]:
        saved: List[str] = []

        subdir_map = {
            "controller": "controllers-extractors",
            "general": "general",
        }

        for query_type, query_text in queries.items():
            subdir = subdir_map.get(query_type, query_type)
            out_dir = os.path.join(self.generated_dir, framework_name, subdir)
            os.makedirs(out_dir, exist_ok=True)

            out_path = os.path.join(out_dir, f"{language}.scm")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(query_text)

            saved.append(out_path)
            logger.debug(
                f"Saved {query_type} query → {out_path}",
                location="QueryWriter.run",
            )

        if mock_files:
            for m_file in mock_files:
                file_type = m_file.get("file_type", "general")
                subdir = subdir_map.get(file_type, file_type)
                out_dir = os.path.join(self.generated_dir, framework_name, subdir)
                os.makedirs(out_dir, exist_ok=True)
                
                filename = m_file.get("filename", f"mock_{file_type}.txt")
                out_path = os.path.join(out_dir, filename)
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(m_file.get("content", ""))
                logger.debug(
                    f"Saved {file_type} mock/draft file → {out_path}",
                    location="QueryWriter.run",
                )

        return {"saved_paths": saved}
