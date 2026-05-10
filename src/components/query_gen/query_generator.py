"""
QueryGenerator — Uses LLM to generate tree-sitter .scm queries from AST dumps.

Reads reference queries from existing .scm files and feeds them along with
the AST S-expression to the LLM for pattern generation.

Capture variable lists for prompts are built dynamically from the existing
reference .scm files — no hardcoded lists.

Chunking strategy:
- Each mock file is processed individually (1 LLM call per file).
- Only the SMALLEST reference .scm is injected as an example to minimise
  prompt size.
- A short delay is inserted between consecutive API calls to prevent
  Vertex rate-limit disconnects.
- Each call is wrapped in an exponential-backoff retry loop so transient
  "Server disconnected" errors are recovered automatically.
"""

import os
import time
from typing import List, Dict

from haystack import component
from haystack.dataclasses import ChatMessage

from src.utils.model_generator import ModelGenerator
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger
from src.components.query_gen.utils import (
    load_ts_language,
    load_smallest_reference_query,
    build_known_captures,
    get_grammar_field_names,
    get_grammar_node_types,
    sanitize_query_fields,
    safe_truncate,
    strip_markdown_fences,
    call_with_retry,
)
from prompts.query_generation_prompts import (
    query_gen_system_prompt,
    query_gen_user_prompt,
)

logger = DocGenLogger(__name__)

# ── Tunables ──────────────────────────────────────────────────────────
MAX_AST_CHARS = 6_000        # hard cap per file AST dump
MAX_SOURCE_CHARS = 4_000     # hard cap per file source code
INTER_CALL_DELAY_S = 2.0     # seconds to sleep between LLM requests
MAX_RETRIES = 3              # retry attempts per LLM call
RETRY_BASE_DELAY_S = 3.0     # base delay for exponential backoff




@component
class QueryGenerator:
    """Generates tree-sitter .scm queries from AST dumps via LLM."""

    def __init__(self, config_path: str = "config.yaml"):
        self.generator = ModelGenerator(
            "query_generator", config_path
        ).get_generator()
        self.config = load_config(config_path)
        general_dir = self.config.get("queries", {}).get("general", "queries/general")
        self.queries_base = os.path.dirname(general_dir)

    def _get_captures_for_prompt(self, query_type: str) -> List[str]:
        """Build the capture list from existing .scm files for the prompt."""
        captures = build_known_captures(self.queries_base, query_type)
        return sorted(f"@{c}" for c in captures)

    # ── main entry point ─────────────────────────────────────────────
    @component.output_types(queries=Dict[str, str])
    def run(
        self,
        ast_results: List[Dict[str, str]],
        language: str,
        framework_name: str,
    ) -> Dict[str, Dict[str, str]]:
        queries: Dict[str, str] = {}

        # Get valid grammar field names for this language
        grammar_fields = get_grammar_field_names(language)
        grammar_fields_block = ", ".join(grammar_fields)
        
        # Get valid grammar node types
        grammar_node_types = get_grammar_node_types(language)
        grammar_node_types_block = ", ".join(grammar_node_types)

        for query_type in ("controller", "general"):
            type_results = [
                r for r in ast_results if r["file_type"] == query_type
            ]
            if not type_results:
                type_results = ast_results

            captures = self._get_captures_for_prompt(query_type)
            extra = ""
            # Use only the smallest reference to keep the prompt lean
            reference = load_smallest_reference_query(
                self.queries_base, query_type
            )
            captures_block = "\n".join(f"   - {c}" for c in captures)

            current_query = ""
            for idx, result in enumerate(type_results):
                # ── throttle consecutive calls ──────────────────────
                if idx > 0 or query_type == "general":
                    time.sleep(INTER_CALL_DELAY_S)

                # ── build compact context ───────────────────────────
                ast_dump = safe_truncate(result["ast_dump"], MAX_AST_CHARS)
                source_code = safe_truncate(result["content"], MAX_SOURCE_CHARS)

                ast_section = f";; --- {result['filename']} ---\n{ast_dump}"
                src_section = f"// --- {result['filename']} ---\n{source_code}"

                iteration_extra = extra
                if current_query:
                    iteration_extra += (
                        "\n--- CURRENT PROGRESS ---\n"
                        "You already generated the following queries from "
                        "previous files.\n"
                        "MERGE these existing patterns with any new patterns "
                        "you see in the current AST.\n"
                        "DO NOT lose the old patterns. Append new patterns "
                        "to this text:\n\n"
                    )
                    iteration_extra += current_query

                system = (
                    query_gen_system_prompt
                    .replace("$required_captures_block", captures_block)
                    .replace("$reference_queries", reference)
                    .replace("$ast_dump", ast_section)
                    .replace("$source_code", src_section)
                    .replace("$grammar_fields", grammar_fields_block)
                    .replace("$grammar_node_types", grammar_node_types_block)
                    .replace("$extra_constraints", iteration_extra)
                )

                messages = [
                    ChatMessage.from_system(system),
                    ChatMessage.from_user(
                        query_gen_user_prompt.substitute(
                            query_type=query_type,
                            framework_name=framework_name,
                            language=language,
                        )
                    ),
                ]

                label = f"{query_type}/{result['filename']}"
                raw = call_with_retry(
                    self.generator, 
                    messages, 
                    label, 
                    max_retries=MAX_RETRIES, 
                    base_delay=RETRY_BASE_DELAY_S
                )
                raw = strip_markdown_fences(raw)
                # Deterministic fix: strip invalid field names the LLM invents
                current_query = sanitize_query_fields(raw, language)

                logger.debug(
                    f"Generated partial {query_type} query from "
                    f"{result['filename']} ({len(current_query)} chars)",
                    location="QueryGenerator.run",
                )

            queries[query_type] = current_query
            logger.debug(
                f"Generated final {query_type} query "
                f"({len(queries[query_type])} chars)",
                location="QueryGenerator.run",
            )

        return {"queries": queries}
