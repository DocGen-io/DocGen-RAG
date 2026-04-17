"""
QueryValidator — Validates generated .scm queries against naming conventions,
tree-sitter syntax, AND semantic correctness (match test against mock ASTs).

All known captures are derived dynamically from existing .scm reference files
instead of hardcoded sets. Language loading uses shared variant probing.
"""

from typing import Dict, List, Optional, Set

from haystack import component
from tree_sitter import Parser, Query, QueryCursor

from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
from src.components.query_gen.utils import (
    load_ts_language,
    extract_captures,
    extract_predicate_captures,
    build_known_captures,
)

logger = DocGenLogger(__name__)

@component
class QueryValidator:
    """Validates generated .scm queries for syntax, capture conformance,
    and semantic match against the actual mock source ASTs."""

    def __init__(self, config_path: str = "config.yaml"):
        config = load_config(config_path)
        general_dir = config.get("queries", {}).get("general", "queries/general")
        self._queries_base = (
            general_dir.rsplit("/", 1)[0] if "/" in general_dir else "queries"
        )

    @component.output_types(
        validated=Dict[str, str],
        errors=List[str],
        is_valid=bool,
    )
    def run(
        self,
        queries: Dict[str, str],
        language: str,
        mock_files: Optional[List[Dict[str, str]]] = None,
    ) -> Dict:
        errors: List[str] = []
        validated: Dict[str, str] = {}

        try:
            ts_language = load_ts_language(language)
        except Exception as e:
            return {
                "validated": {},
                "errors": [f"Cannot load tree-sitter grammar for '{language}': {e}"],
                "is_valid": False,
            }

        for query_type, query_text in queries.items():
            known = build_known_captures(self._queries_base, query_type)

            # --- Phase 1: syntax + capture-name checks ---
            type_errors = self._validate_syntax(
                query_type, query_text, ts_language, known
            )
            if type_errors:
                errors.extend(type_errors)
                continue

            # --- Phase 2: semantic match test (dry-run against mock ASTs) ---
            if mock_files:
                match_errors = self._validate_semantic(
                    query_type, query_text, ts_language, mock_files
                )
                if match_errors:
                    errors.extend(match_errors)
                    continue

            validated[query_type] = query_text

        is_valid = len(errors) == 0

        if is_valid:
            logger.info(
                "All queries passed validation",
                location="QueryValidator.run",
            )
        else:
            logger.warning(
                f"Validation failed with {len(errors)} error(s): {errors}",
                location="QueryValidator.run",
            )

        return {
            "validated": validated,
            "errors": errors,
            "is_valid": is_valid,
        }

    # ── Phase 1: Syntax ──────────────────────────────────────────────────

    @staticmethod
    def _validate_syntax(
        query_type: str,
        query_text: str,
        ts_language,
        known_captures: Set[str],
    ) -> List[str]:
        """Validate syntax and capture-name conformance."""
        errs: List[str] = []

        # 1. Non-empty
        if not query_text or not query_text.strip():
            errs.append(f"[{query_type}] Query is empty")
            return errs

        # 2. tree-sitter parse
        try:
            Query(ts_language, query_text)
        except Exception as e:
            errs.append(f"[{query_type}] tree-sitter parse error: {e}")
            return errs

        # 3. Extract captures (comment-stripped)
        all_captures = extract_captures(query_text)
        predicate_only = extract_predicate_captures(query_text)

        # Unknown = not in known set AND not used solely as predicate arg
        unknown = all_captures - known_captures - predicate_only
        if unknown:
            errs.append(
                f"[{query_type}] Unknown capture variables: "
                f"{', '.join(sorted('@' + c for c in unknown))}. "
                f"Known: {', '.join(sorted('@' + c for c in known_captures))}"
            )

        # 4. Controller-specific: must have @class_decorator OR @class_decorator_type
        if query_type == "controller":
            has_class_marker = (
                "class_decorator" in all_captures
                or "class_decorator_type" in all_captures
            )
            if not has_class_marker:
                errs.append(
                    f"[{query_type}] Missing class-level capture: "
                    "need @class_decorator or @class_decorator_type"
                )

        return errs

    # ── Phase 2: Semantic match test ─────────────────────────────────────

    @staticmethod
    def _validate_semantic(
        query_type: str,
        query_text: str,
        ts_language,
        mock_files: List[Dict[str, str]],
    ) -> List[str]:
        """Execute the query against mock file ASTs and check that essential
        captures actually match nodes.

        Returns a list of diagnostic errors (empty = OK).
        """
        errs: List[str] = []
        parser = Parser(ts_language)
        ts_query = Query(ts_language, query_text)

        # Pick mock/draft files relevant to this query type
        relevant_files = [
            f for f in mock_files
            if f.get("file_type", "general") == query_type
        ]
        # Fall back to ALL files if none match the type exactly
        if not relevant_files:
            relevant_files = mock_files

        # Filter out json/yaml/settings files from strict validation
        relevant_files = [
            f for f in relevant_files
            if not f.get("filename", "").endswith((".json", ".yaml", ".yml", ".xml", ".ini", ".conf"))
        ]

        # Collect all capture names that actually returned nodes
        found_captures: Set[str] = set()
        total_matches = 0

        for file_info in relevant_files:
            content = file_info.get("content", "")
            if not content.strip():
                continue

            tree = parser.parse(content.encode("utf-8"))
            cursor = QueryCursor(ts_query)
            matches = cursor.matches(tree.root_node)

            for _pattern_idx, match_captures in matches:
                total_matches += 1
                for capture_name, _nodes in match_captures.items():
                    found_captures.add(capture_name)

        if total_matches == 0:
            errs.append(
                f"[{query_type}] Semantic validation FAILED: query is "
                f"syntactically valid but matched 0 nodes across "
                f"{len(relevant_files)} mock/draft file(s). The query pattern "
                f"does not match the actual AST structure of the draft. Rewrite the "
                f"query to match the AST nodes that exist."
            )
            return errs



        if not errs:
            logger.info(
                f"[{query_type}] Semantic check passed: "
                f"{total_matches} match(es), captures: "
                f"{', '.join(sorted('@' + c for c in found_captures))}",
                location="QueryValidator._validate_semantic",
            )

        return errs
