"""
Prompts for the Tree-sitter Query Generation Pipeline.

Used by MockFileGenerator and QueryGenerator components to produce
framework-specific .scm queries via LLM.
"""

from string import Template

# ─────────────────────────────────────────────────────────────
# 1. MOCK FILE GENERATION
# ─────────────────────────────────────────────────────────────

micro_snippet_system_prompt = """\
You are an expert software engineer prioritizing highly exhaustive syntax coverage.
Your ONLY job is to generate as many DISTINCT micro-snippets (tiny 1-5 line code blocks)
as possible for a given framework/language. These will be used for unit-testing AST parsers.

2. If valid, generate 15 to 30 EXHAUSTIVE microscopic code snippets covering EVERY possible variation:
   - Controllers/Routers with ALL HTTP method variations.
   - Component groupings like `APIRouter(prefix=...)`, `Express.Router`.
   - Dependency injections, context parameters, path/query parameters.
   - Class-based and function-based handlers.
   - Exported and non-exported declarations.
   - Arrow functions, standard functions, nested functions.
   - DTOs, Interfaces, Records, Type aliases, Enums.
   
3. CRITICAL LIMITATION: EACH SNIPPET MUST BE ISOLATED AND MICRO-SIZED (1-5 lines max).
   DO NOT write a full API server. Write JUST the exact route definition or class definition snippet.

4. Output MUST use XML tags, NOT JSON. Wrap everything in `<snippets>`.
   If the framework/language is INVALID, output EXACTLY:
   <error>Invalid framework or language</error>
   
   Otherwise, for each micro-snippet, use `<snippet type="controller">` or `<snippet type="general">` 
   and put the raw source code inside.
   Example:
   <snippets>
     <snippet type="controller">
     @app.post("/users")
     async def create_user(user: User): pass
     </snippet>
     <snippet type="controller">
     export const route = (req, res) => res.send();
     </snippet>
     <snippet type="general">
     export interface User { id: string }
     </snippet>
     <snippet type="general">
     class DatabaseService {}
     </snippet>
   </snippets>

5. Code must be syntactically valid and parseable. Do NOT include markdown blocks.
"""

micro_snippet_user_prompt = Template(
    "Generate 15 to 30 exhaustive micro-snippets for the **$framework_name** framework "
    "using the **$language** programming language.\n\n"
    "Cover every possible syntax variation for controllers/routers AND "
    "general structures (classes, interfaces, DTOs). Keep each exactly 1-5 lines."
)

# ─────────────────────────────────────────────────────────────
# 2. QUERY GENERATION
# ─────────────────────────────────────────────────────────────

query_gen_system_prompt = """\
You are an expert in tree-sitter S-expression query patterns (.scm files).
Your ONLY job is to generate a tree-sitter .scm query that extracts structured
code elements from an AST.

CRITICAL RULES:
1. Output ONLY the raw .scm query text. No JSON wrapping, no markdown, no explanation.
2. ALLOWED CAPTURES: You may ONLY use capture variable names from the list below. 
   You DO NOT need to use all of them—use only what makes sense for the code snippet!
   DO NOT invent any new capture names.

$required_captures_block

3. Study the reference queries below to understand the exact patterns and naming:

--- REFERENCE QUERIES ---
$reference_queries
--- END REFERENCE ---

4. Study the AST structure below and write patterns that match the nodes correctly:

--- AST S-EXPRESSION ---
$ast_dump
--- END AST ---

5. Study the source code that produced this AST:

--- SOURCE CODE ---
$source_code
--- END SOURCE ---

6. The query must:
   - NOT be empty
   - Parse without errors in tree-sitter
   - Cover all major patterns (classes, functions, decorators) but DO NOT match exact variable/function literal string names unless necessary.
   - Be CONCISE and GENERIC. Write simple abstracted queries. DO NOT write an individual block for every variable in the file.
   - **CRITICAL**: Use GENERIC AST matching (e.g. `(function_definition name: (identifier) @method_name)`). DO NOT hardcode the exact number of `parameters` or `arguments` found in the mock file AST! A query should match ANY function, regardless of how many parameters it has.
   - Use proper tree-sitter query syntax: node types, field names, alternations [], predicates #eq?/#match?

7. CRITICAL — VALID GRAMMAR FIELD NAMES:
   The ONLY valid field names you may use with `field_name:` syntax for this language are:
   $grammar_fields
   If a field name is NOT in this list, you MUST NOT use `field_name: (...)` syntax.
   Instead, use anonymous child matching: `(parent_node (child_node) @cap)`.

8. CRITICAL — VALID GRAMMAR NODE TYPES:
   You MUST ONLY use node types that actually exist in the language grammar.
   For example, if you are analyzing Python, DO NOT invent `(interface_definition)`.
   The exact valid node types you are allowed to use are:
   $grammar_node_types

9. QUERY SYNTAX PITFALLS — NEVER DO THESE:
   - WRONG: `(node_type @capture_name)` — NEVER put the capture inside the parentheses.
   - RIGHT: `(node_type) @capture_name` — ALWAYS put the capture AFTER the closing parenthesis.
   - WRONG: `decorator: (call)` — `decorator` is a node type, not a field name in Python.
   - RIGHT: `(decorator (call))` — Match it as a nested node.
   - WRONG: `(identifier) @decorator_path #match?(@decorator_path "^app\\.")` — Invalid predicate syntax.
   - RIGHT: `(identifier) @decorator_path (#match? @decorator_path "^app\\.")` — Predicates must be wrapped in `(#...)`.

$extra_constraints
"""

query_gen_user_prompt = Template(
    "Generate a **$query_type** tree-sitter .scm query for **$framework_name** "
    "($language) based on the AST and source code provided in the system prompt."
)

# ─────────────────────────────────────────────────────────────
# 3. QUERY REPAIR (used on validation failure)
# ─────────────────────────────────────────────────────────────

query_repair_system_prompt = """\
You are a tree-sitter query repair specialist. A previously generated .scm query
has validation errors. Fix the query so it passes all checks.

RULES:
1. Output ONLY the corrected .scm query text. No JSON, no markdown, no explanation.
2. ALLOWED CAPTURES: You may ONLY use capture variable names from the list below.
   You DO NOT need to use all of them—use only what makes sense for the code snippet!
3. The query must parse without tree-sitter syntax errors.
4. VALID GRAMMAR FIELD NAMES for this language:
   $grammar_fields
   The `field_name:` syntax is ONLY valid for names in this list.
   `decorator` is a NODE TYPE, not a field name. Never write `decorator: (...)`.   
   CORRECT:  (decorated_definition (decorator (identifier) @cap) definition: (...))
   WRONG:    (decorated_definition decorator: (identifier) @cap)
5. VALID GRAMMAR NODE TYPES:
   $grammar_node_types
   You MUST NEVER use a node type outside this list! For example, NO `interface_definition` in Python.

ERRORS TO FIX:
$errors

ORIGINAL QUERY:
$original_query

ALLOWED CAPTURE NAMES:
$allowed_captures

REFERENCE QUERY (for correct patterns):
$reference_queries
"""

query_repair_user_prompt = "Fix the tree-sitter query above. Output ONLY the corrected .scm query."
