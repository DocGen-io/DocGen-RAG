"""
DraftParser — Loads user-defined draft files from disk, parsing them via tree-sitter
and returning AST S-expressions alongside the chunked content.

Draft files act as a strict gold-standard for what the Tree-Sitter SCM query must
extract, replacing LLM-generated mock files with human-curated examples.
"""

import os
from typing import List, Dict

from haystack import component
from tree_sitter import Parser

from src.utils.logger import DocGenLogger
from src.components.query_gen.utils import load_ts_language
from src.utils.config_loader import load_config

logger = DocGenLogger(__name__)


@component
class DraftParser:
    """Loads and parses draft files from disk, producing AST S-expression dumps."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        config = load_config(config_path)
        self.drafts_base = config.get("queries", {}).get("drafts", "queries/drafts")

    @component.output_types(ast_results=List[Dict[str, str]], mock_files=List[Dict[str, str]])
    def run(
        self,
        framework_name: str,
        language: str,
        draft_dir: str = None,
    ) -> Dict[str, List[Dict[str, str]]]:
        """Loads all draft files for the given framework/language.
        
        If draft_dir is not provided, constructs it from {drafts_base}/{framework_name}/{language}
        """
        if not draft_dir:
            draft_dir = os.path.join(self.drafts_base, framework_name.lower(), language.lower())

        if not os.path.isdir(draft_dir):
            raise ValueError(f"Draft directory not found: {draft_dir}")

        ts_language = load_ts_language(language)
        parser = Parser(ts_language)
        results: List[Dict[str, str]] = []
        mock_files: List[Dict[str, str]] = []

        for fname in os.listdir(draft_dir):
            fpath = os.path.join(draft_dir, fname)
            if not os.path.isfile(fpath):
                continue
            
            # Determine file_type by looking at the filename or placing in subdirs.
            # E.g. controller_draft.py -> "controller"
            file_type = "general"
            if "controller" in fname.lower():
                file_type = "controller"

            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                logger.warning(
                    f"Skipping empty draft file: {fname}",
                    location="DraftParser.run",
                )
                continue

            code_bytes = content.encode("utf-8")
            tree = parser.parse(code_bytes)
            ast_sexp = str(tree.root_node)

            result_dict = {
                "filename": fname,
                "content": content,
                "file_type": file_type,
                "ast_dump": ast_sexp,
            }
            results.append(result_dict)
            
            mock_files.append({
                "filename": fname,
                "content": content,
                "file_type": file_type
            })

            logger.info(
                f"Parsed AST for draft {fname} ({len(ast_sexp)} chars)",
                location="DraftParser.run",
            )

        if not results:
            raise ValueError(f"No valid draft files found in {draft_dir}")

        # Returns both ast_results (for prompt) and mock_files (for validator compatibility)
        return {
            "ast_results": results,
            "mock_files": mock_files
        }
