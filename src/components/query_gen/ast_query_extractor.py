"""
ASTQueryExtractor — Parses mock source code via tree-sitter and returns AST S-expressions.

Uses shared language loading from utils (no static alias map).
"""

from typing import List, Dict

from haystack import component
from tree_sitter import Parser

from src.utils.logger import DocGenLogger
from src.components.query_gen.utils import load_ts_language

logger = DocGenLogger(__name__)


@component
class ASTQueryExtractor:
    """Parses mock source files via tree-sitter and produces AST S-expression dumps."""

    @component.output_types(ast_results=List[Dict[str, str]])
    def run(
        self,
        mock_files: List[Dict[str, str]],
        language: str,
    ) -> Dict[str, List[Dict[str, str]]]:
        ts_language = load_ts_language(language)
        parser = Parser(ts_language)
        results: List[Dict[str, str]] = []

        for file_info in mock_files:
            filename = file_info.get("filename", "unknown")
            content = file_info.get("content", "")
            file_type = file_info.get("file_type", "general")

            if not content.strip():
                logger.warning(
                    f"Skipping empty mock file: {filename}",
                    location="ASTQueryExtractor.run",
                )
                continue

            code_bytes = content.encode("utf-8")
            tree = parser.parse(code_bytes)
            ast_sexp = str(tree.root_node)

            results.append(
                {
                    "filename": filename,
                    "content": content,
                    "file_type": file_type,
                    "ast_dump": ast_sexp,
                }
            )

            logger.info(
                f"Parsed AST for {filename} ({len(ast_sexp)} chars)",
                location="ASTQueryExtractor.run",
            )

        if not results:
            raise ValueError("No mock files could be parsed by tree-sitter")

        return {"ast_results": results}
