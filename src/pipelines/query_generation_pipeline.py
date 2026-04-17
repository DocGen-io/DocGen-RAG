"""
QueryGenerationPipeline — Orchestrates tree-sitter .scm query generation for new frameworks.

Workflow:
    1. MockFileGenerator  → representative mock source files via LLM
    2. ASTQueryExtractor  → tree-sitter parse → AST S-expressions
    3. QueryGenerator     → LLM generates .scm queries from AST + source + reference
    4. QueryValidator     → validates capture vars + syntax
       ↳ On failure: repair prompt → re-generate → re-validate (up to max_retries)
    5. QueryWriter        → saves validated queries to disk

Usage:
    uv run python -m src.pipelines.query_generation_pipeline --framework FastAPI --language python
"""

import httpx

# --- GLOBALLY PATCH HTTPX TIMEOUT ---
# The google-genai SDK has a strict short timeout that causes LLM disconnects
# during long AST-to-query generation steps. We patch the underlying client to wait longer.
from httpx import Timeout
_original_client_init = httpx.Client.__init__

def _patched_client_init(self, *args, **kwargs):
    kwargs["timeout"] = Timeout(300.0)
    _original_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _patched_client_init
# ------------------------------------

import argparse
import sys
from typing import Dict, List

from haystack.dataclasses import ChatMessage

from src.components.query_gen.mock_file_generator import MicroSnippetGenerator
from src.components.query_gen.ast_query_extractor import ASTQueryExtractor
from src.components.query_gen.draft_parser import DraftParser
from src.components.query_gen.query_generator import QueryGenerator
from src.components.query_gen.query_validator import QueryValidator
from src.components.query_gen.query_writer import QueryWriter
from src.utils.model_generator import ModelGenerator
from src.utils.logger import DocGenLogger
from prompts.query_generation_prompts import (
    query_repair_system_prompt,
    query_repair_user_prompt,
)
from src.components.query_gen.utils import (
    build_known_captures,
    call_with_retry,
    strip_markdown_fences,
)

logger = DocGenLogger(__name__)


class QueryGenerationPipeline:
    """
    Orchestrates end-to-end tree-sitter query generation with retry loops.

    Not a Haystack Pipeline graph — uses Haystack @component instances
    composed via Python control flow because the retry logic is per-query-type
    with error feedback, which doesn't map cleanly to Haystack's
    max_runs_per_component loop mechanism.
    """

    def __init__(self, config_path: str = "config.yaml", max_retries: int = 3, use_drafts: bool = False):
        self.config_path = config_path
        self.max_retries = max_retries
        self.use_drafts = use_drafts

        if not self.use_drafts:
            self.snippet_gen = MicroSnippetGenerator(config_path=config_path)
            self.ast_extractor = ASTQueryExtractor()
        else:
            self.draft_parser = DraftParser(config_path=config_path)

        self.query_gen = QueryGenerator(config_path=config_path)
        self.validator = QueryValidator(config_path=config_path)
        self.writer = QueryWriter(config_path=config_path)

        # Separate generator for repair prompts
        self.repair_generator = ModelGenerator(
            "query_generator", config_path
        ).get_generator()

    def run(self, framework_name: str, language: str) -> Dict[str, List[str]]:
        """
        Execute the full pipeline.

        Args:
            framework_name: Target framework (e.g. "FastAPI", "Express", "Spring").
            language: Programming language (e.g. "python", "typescript", "java").

        Returns:
            Dict with "saved_paths" listing the written .scm file paths.

        Raises:
            ValueError: If framework/language is invalid or all retries exhausted.
        """
        logger.info(
            f"Starting query generation for {framework_name}/{language}",
            location="QueryGenerationPipeline.run",
        )

        if self.use_drafts:
            logger.info("Using draft files for querying", location="QueryGenerationPipeline.run")
            draft_result = self.draft_parser.run(
                framework_name=framework_name, language=language
            )
            ast_results = draft_result["ast_results"]
            mock_files = draft_result["mock_files"]
        else:
            # Step 1: Generate micro-snippets
            snippet_result = self.snippet_gen.run(
                framework_name=framework_name, language=language
            )
            mock_files = snippet_result["snippets"]

            # Step 2: Parse ASTs
            ast_result = self.ast_extractor.run(
                mock_files=mock_files, language=language
            )
            ast_results = ast_result["ast_results"]

        # Step 3+4: Generate + validate with retry loop ON EACH ISOLATED SNIPPET
        validated_queries_by_type = {"controller": [], "general": []}
        
        for mock_file, ast_result in zip(mock_files, ast_results):
            try:
                # Run the atomic TDD loop for this specific snippet
                queries = self._generate_with_retry(
                    ast_results=[ast_result],
                    language=language,
                    framework_name=framework_name,
                    mock_files=[mock_file],
                )
                
                # Append passing queries to our aggregator sets
                if "controller" in queries and queries["controller"]:
                    validated_queries_by_type["controller"].append(queries["controller"])
                if "general" in queries and queries["general"]:
                    validated_queries_by_type["general"].append(queries["general"])
                    
            except ValueError as e:
                logger.warning(
                    f"Skipping snippet {mock_file.get('filename')} due to unresolved generation errors: {e}",
                    location="QueryGenerationPipeline.run",
                )

        # Step 5: Merge isolated queries
        final_queries = {}
        for q_type, q_list in validated_queries_by_type.items():
            if q_list:
                # Tree-sitter allows multiple abstract patterns stacked sequentially in an SCM
                final_queries[q_type] = "\n\n".join(q_list)

        # Step 6: Write to disk
        write_result = self.writer.run(
            queries=final_queries,
            framework_name=framework_name,
            language=language,
            mock_files=mock_files,
        )

        logger.info(
            f"Pipeline complete. Saved {len(write_result['saved_paths'])} queries",
            location="QueryGenerationPipeline.run",
        )

        return write_result

    def _generate_with_retry(
        self,
        ast_results: List[Dict[str, str]],
        language: str,
        framework_name: str,
        mock_files: List[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Generate queries with retry loop on validation failure."""
        # Initial generation
        gen_result = self.query_gen.run(
            ast_results=ast_results,
            language=language,
            framework_name=framework_name,
        )
        queries = gen_result["queries"]

        for attempt in range(self.max_retries):
            val_result = self.validator.run(
                queries=queries, language=language, mock_files=mock_files
            )

            if val_result["is_valid"]:
                logger.info(
                    f"Queries validated on attempt {attempt + 1}",
                    location="QueryGenerationPipeline._generate_with_retry",
                )
                return val_result["validated"]

            errors = val_result["errors"]
            logger.warning(
                f"Attempt {attempt + 1}/{self.max_retries} failed: {errors}",
                location="QueryGenerationPipeline._generate_with_retry",
            )
            # Logging is handled by `logger.warning` above

            # Repair only the failed queries
            repaired = dict(val_result["validated"])  # keep the good ones
            failed_types = set()
            for err in errors:
                if err.startswith("[controller]"):
                    failed_types.add("controller")
                elif err.startswith("[general]"):
                    failed_types.add("general")

            for query_type in failed_types:
                repaired_query = self._repair_query(
                    query_type=query_type,
                    original_query=queries.get(query_type, ""),
                    errors=[e for e in errors if e.startswith(f"[{query_type}]")],
                    language=language,
                )
                repaired[query_type] = repaired_query

            queries = repaired

        # Final validation after all retries
        final_result = self.validator.run(
            queries=queries, language=language, mock_files=mock_files
        )
        if final_result["is_valid"]:
            return final_result["validated"]

        raise ValueError(
            f"Query generation failed after {self.max_retries} retries. "
            f"Remaining errors: {final_result['errors']}"
        )

    def _repair_query(
        self,
        query_type: str,
        original_query: str,
        errors: List[str],
        language: str,
    ) -> str:
        """Use LLM to repair a failed query based on error feedback."""
        import time

        captures = build_known_captures(self.query_gen.queries_base, query_type)
        allowed_str = ", ".join(sorted(f"@{c}" for c in captures))

        # Use smallest reference to keep repair prompt compact
        from src.components.query_gen.utils import (
            load_smallest_reference_query,
            get_grammar_field_names,
            get_grammar_node_types,
        )
        reference = load_smallest_reference_query(
            self.query_gen.queries_base, query_type
        )
        grammar_fields = ", ".join(get_grammar_field_names(language))
        grammar_node_types = ", ".join(get_grammar_node_types(language))

        system = query_repair_system_prompt.replace(
            "$errors", "\n".join(errors)
        ).replace(
            "$original_query", original_query
        ).replace(
            "$allowed_captures", allowed_str
        ).replace(
            "$grammar_fields", grammar_fields
        ).replace(
            "$grammar_node_types", grammar_node_types
        ).replace(
            "$reference_queries", reference
        )

        messages = [
            ChatMessage.from_system(system),
            ChatMessage.from_user(query_repair_user_prompt),
        ]

        # Standardized call with retry and backoff
        query_text = call_with_retry(
            self.repair_generator, 
            messages, 
            f"Repair-{query_type}",
            max_retries=3,
            base_delay=3.0
        )
        query_text = strip_markdown_fences(query_text)

        # Deterministic fix: strip invalid field names the LLM invents
        from src.components.query_gen.utils import sanitize_query_fields
        query_text = sanitize_query_fields(query_text.strip(), language)
        return query_text


def main():
    from dotenv import load_dotenv
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Generate tree-sitter .scm queries for a framework"
    )
    parser.add_argument(
        "--framework", required=True, help="Framework name (e.g. FastAPI, Express, Spring)"
    )
    parser.add_argument(
        "--language", required=True, help="Language (e.g. python, typescript, java)"
    )
    parser.add_argument(
        "--max-retries", type=int, default=3, help="Max retry attempts (default: 3)"
    )
    parser.add_argument(
        "--config", default="config.yaml", help="Path to config.yaml"
    )
    parser.add_argument(
        "--use-drafts", action="store_true", help="Use draft files instead of mock generation"
    )

    args = parser.parse_args()

    pipeline = QueryGenerationPipeline(
        config_path=args.config,
        max_retries=args.max_retries,
        use_drafts=args.use_drafts,
    )

    try:
        result = pipeline.run(
            framework_name=args.framework,
            language=args.language,
        )
        print(f"\nSaved queries to:")
        for path in result["saved_paths"]:
            print(f"  {path}")
    except ValueError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
