"""
Shared utilities for the query generation pipeline.

Provides:
- Dynamic tree-sitter language loading (no static alias map)
- Dynamic capture extraction from existing .scm reference files
- SCM text parsing helpers (comment stripping, capture regex)
"""

import os
import re
from typing import Dict, Set

from tree_sitter_language_pack import get_language

from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

_COMMENT_RE = re.compile(r";;.*$", re.MULTILINE)
_CAPTURE_RE = re.compile(r"@([a-zA-Z_][a-zA-Z0-9_]*)")
_PREDICATE_CAPTURE_RE = re.compile(
    r"#(?:eq|match|not-eq|not-match|any-of|is|is-not)\?\s+@([a-zA-Z_][a-zA-Z0-9_]*)"
)

_QUERY_SUBDIR = {
    "controller": "controllers-extractors",
    "general": "general",
}


# ── Language loading ───────────────────────────────────────────────────

def load_ts_language(language: str):
    """
    Load a tree-sitter Language, trying name variants automatically.

    Mirrors BaseASTExtractor._load_language from the main codebase so that
    every grammar (including c_sharp) resolves without a static alias table.
    """
    base = language.lower().strip()
    candidates = {
        base,
        base.replace("_", ""),
        base.replace("sharp", "_sharp"),
    }
    for name in candidates:
        try:
            lang = get_language(name)
            if lang:
                return lang
        except Exception:
            continue
    raise ValueError(
        f"No tree-sitter grammar found for '{language}' (tried: {sorted(candidates)})"
    )


def get_grammar_field_names(language: str) -> list[str]:
    """Return all valid field names for a tree-sitter language grammar.

    This is used to inject the list of allowed field names into the LLM
    prompt so it never invents non-existent field names like `decorator:`
    or `call:`.
    """
    lang = load_ts_language(language)
    names = []
    for fid in range(1, lang.field_count + 1):
        name = lang.field_name_for_id(fid)
        if name:
            names.append(name)
    return sorted(names)


def get_grammar_node_types(language: str) -> list[str]:
    """Return all valid node types for a tree-sitter language grammar.
    Helps prevent the LLM from hallucinating non-existent node types.
    """
    lang = load_ts_language(language)
    names = set()
    for i in range(lang.node_kind_count):
        name = lang.node_kind_for_id(i)
        if name and name.isidentifier():
            names.add(name)
    return sorted(names)


def sanitize_query_fields(query_text: str, language: str) -> str:
    """Fixes tree-sitter queries where a node type is used as a field name.

    LLMs frequently emit patterns like ``decorator: (call ...)`` where
    ``decorator`` is a *node type*, not a grammar field. This function
    detects these cases. If the word before the colon is a valid node type
    for the language but NOT a valid field, it transforms the qualifier 
    into a nested node: ``(decorator (call ...))``.
    """
    valid_fields = set(get_grammar_field_names(language))
    
    # We need the node types to check if the 'fake field' is actually a node type
    node_types = set(get_grammar_node_types(language))

    # Regex matches `word: (` 
    pattern = re.compile(r"([a-z_]+):\s*\(")
    
    offset = 0
    result = query_text
    
    for m in pattern.finditer(query_text):
        name = m.group(1)
        if name in valid_fields:
            continue
            
        # If it's not a field, check if it's a node type
        if name in node_types:
            # It's a node type being used as a field! 
            # Transform `name: (` -> `(name (` and add a `)` at the end of this block.
            start_pos = m.start() + offset
            colon_paren_pos = m.end() - 1 + offset # point at the `(`
            
            # Find the matching closing paren for the one at colon_paren_pos
            depth = 0
            end_pos = -1
            for i in range(colon_paren_pos, len(result)):
                if result[i] == '(':
                    depth += 1
                elif result[i] == ')':
                    depth -= 1
                    if depth == 0:
                        end_pos = i
                        break
            
            if end_pos != -1:
                # 1. Replace `name: (` with `(name (`
                # 2. Add `)` after end_pos
                prefix = result[:start_pos]
                inner = result[colon_paren_pos:end_pos+1]
                suffix = result[end_pos+1:]
                
                new_block = f"({name} {inner})"
                old_len = end_pos + 1 - start_pos
                result = prefix + new_block + suffix
                offset += (len(new_block) - old_len)
        else:
            # It's neither a field nor a known node type. 
            # Just strip the `name:` part entirely.
            start_pos = m.start() + offset
            colon_pos = m.end() - 1 + offset
            result = result[:start_pos] + result[colon_pos:]
            offset -= (colon_pos - start_pos)

    return result


# ── SCM text helpers ──────────────────────────────────────────────────

def strip_comments(text: str) -> str:
    """Remove ;; comments from .scm query text."""
    return _COMMENT_RE.sub("", text)


def extract_captures(query_text: str) -> Set[str]:
    """Return all @capture names from a .scm query (ignoring comments)."""
    return set(_CAPTURE_RE.findall(strip_comments(query_text)))


def extract_predicate_captures(query_text: str) -> Set[str]:
    """Return captures used inside predicates (#eq?, #match?, etc.)."""
    return set(_PREDICATE_CAPTURE_RE.findall(strip_comments(query_text)))


# ── Reference query loading ──────────────────────────────────────────

def _get_queries_base(config_path: str = "config.yaml") -> str:
    """Return the parent directory that contains controllers-extractors/ and general/."""
    config = load_config(config_path)
    general_dir = config.get("queries", {}).get("general", "queries/general")
    return os.path.dirname(general_dir)




def load_smallest_reference_query(queries_base: str, query_type: str) -> str:
    """Return the SMALLEST .scm file as a compact formatting example.

    Sending all reference files inflates the system prompt and causes API
    timeouts with smaller models.  One well-chosen example is enough for
    the LLM to learn the capture naming conventions.
    """
    subdir = _QUERY_SUBDIR.get(query_type, query_type)
    ref_dir = os.path.join(queries_base, subdir)

    if not os.path.isdir(ref_dir):
        return "(no reference queries available)"

    smallest_name = None
    smallest_size = float("inf")
    for fname in os.listdir(ref_dir):
        if not fname.endswith(".scm"):
            continue
        fpath = os.path.join(ref_dir, fname)
        size = os.path.getsize(fpath)
        if size < smallest_size:
            smallest_size = size
            smallest_name = fname

    if smallest_name is None:
        return "(no reference queries available)"

    with open(os.path.join(ref_dir, smallest_name), "r", encoding="utf-8") as f:
        content = f.read()
    return f";; === {smallest_name} (example) ===\n{content}"


def build_known_captures(queries_base: str, query_type: str) -> Set[str]:
    """
    Dynamically build the set of known capture names by scanning every
    existing .scm file of the given type.

    This is the ONLY source of truth — no hardcoded sets.
    """
    subdir = _QUERY_SUBDIR.get(query_type, query_type)
    ref_dir = os.path.join(queries_base, subdir)

    if not os.path.isdir(ref_dir):
        return set()

    captures: Set[str] = set()
    for fname in os.listdir(ref_dir):
        if not fname.endswith(".scm"):
            continue
        with open(os.path.join(ref_dir, fname), "r", encoding="utf-8") as f:
            text = f.read()
        file_captures = extract_captures(text)
        predicate_only = extract_predicate_captures(text)
        captures |= file_captures - predicate_only

    return captures


# ── LLM Helpers ──────────────────────────────────────────────────────

def safe_truncate(text: str, limit: int) -> str:
    """Truncate *text* at a clean line boundary so the LLM never sees
    broken S-expressions or half-written source lines."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rfind("\n")
    if cut < limit // 2:          # degenerate — just hard-cut
        cut = limit
    return text[:cut] + "\n;; ... (truncated for brevity)"


def strip_markdown_fences(text: str) -> str:
    """Remove leading/trailing ``` fences that some models add."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]                       # drop opening ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]                   # drop closing ```
        text = "\n".join(lines)
    return text.strip()


def call_with_retry(
    generator, 
    messages: list, 
    label: str, 
    max_retries: int = 3, 
    base_delay: float = 2.0
) -> str:
    """Call `generator.run(messages=messages)` with exponential backoff."""
    import time
    for attempt in range(1, max_retries + 1):
        try:
            response = generator.run(messages=messages)["replies"][0]
            return response.text if hasattr(response, "text") else str(response)
        except Exception as exc:
            if attempt == max_retries:
                raise
            wait = base_delay * (2 ** (attempt - 1))
            logger.warning(
                f"[{label}] Attempt {attempt}/{max_retries} failed: {exc!r}. "
                f"Retrying in {wait:.0f}s …",
                location="utils.call_with_retry",
            )
            time.sleep(wait)
    raise RuntimeError("call_with_retry exhausted retries")
