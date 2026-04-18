#!/usr/bin/env bash
# action-entrypoint.sh
set -euo pipefail

WEAVIATE_URL="${INPUT_WEAVIATE_URL:-}"

if [ -z "$WEAVIATE_URL" ]; then
  echo "::error:: 'weaviate-url' is required. Please provide a persistent Weaviate instance URL."
  exit 1
fi

if echo "$WEAVIATE_URL" | grep -qiE '(localhost|127\.0\.0\.1|0\.0\.0\.0|weaviate:)'; then
  echo "::error:: DocGen requires a PERSISTENT Weaviate instance."
  echo "::error:: Transient (localhost) Weaviate is not supported because data is destroyed between CI runs."
  exit 1
fi

export WEAVIATE_URL="${INPUT_WEAVIATE_URL}"
export WEAVIATE_API_KEY="${INPUT_WEAVIATE_API_KEY:-}"
export GEMINI_API_KEY="${INPUT_GEMINI_API_KEY:-}"
export GOOGLE_CLOUD_PROJECT="${INPUT_GOOGLE_CLOUD_PROJECT:-}"
export GOOGLE_CLOUD_LOCATION="${INPUT_GOOGLE_CLOUD_LOCATION:-}"

PATH_DIR="${INPUT_PATH:-.}"
API_DIR="${INPUT_API_DIR:-}"
LLM_PROVIDER="${INPUT_LLM_PROVIDER:-gemini}"
LLM_MODEL="${INPUT_LLM_MODEL:-gemini-2.5-flash-lite}"
ACTIVE_EMBEDDER="${INPUT_ACTIVE_EMBEDDER:-gemini}"
EMBEDDING_MODEL="${INPUT_EMBEDDING_MODEL:-gemini-2.5-flash-lite}"
CHUNK_SIZE="${INPUT_CHUNK_SIZE:-500}"
TOP_K="${INPUT_TOP_K:-2}"
AUTO_GROUP="${INPUT_AUTO_GROUP:-false}"

if [ "$LLM_PROVIDER" = "gemini" ] || [ "$ACTIVE_EMBEDDER" = "gemini" ]; then
  if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "::error:: 'gemini-api-key' is required when llm-provider or active-embedder is 'gemini'."
    exit 1
  fi
fi

cat > /docgen/config.yaml << YAML
rag:
  active_embedder: "${ACTIVE_EMBEDDER}"
  embedding_model: "${EMBEDDING_MODEL}"
  top_k_retriever: ${TOP_K}
  top_k_reranker: ${TOP_K}
  chunk_size: ${CHUNK_SIZE}

process_grouping_automatically: ${AUTO_GROUP}

WEAVIATE_URL: "${WEAVIATE_URL}"
WEAVIATE_API_KEY: "${WEAVIATE_API_KEY}"
tracing: false

code_analyzer:
  active_generator: "${LLM_PROVIDER}"
  analyzer_output_path: "analyzer_output"
  dependency_search_top_k: 100

generators:
  gemini:
    project_id: "${GOOGLE_CLOUD_PROJECT}"
    location: "${GOOGLE_CLOUD_LOCATION}"
    model: "${LLM_MODEL}"
    max_tokens: 8192

doc_creator:
  active_generator: "${LLM_PROVIDER}"
  output_dir: "output"

doc_merger:
  api_title: "API Documentation"
  api_version: "1.0.0"
  api_description: "Auto-generated REST API documentation"
  base_url: "http://localhost:3000"

app:
  environment: "production"

query_generator:
  active_generator: "${LLM_PROVIDER}"

ast_extractor:
  save_ast: false
  save_ast_path: "analyzer_output/ast"
  verbose: false

queries:
  general: "queries/general"
  controllers: "queries/controllers-extractors"
  generated: "queries/generated"

api_frameworks: ["NestJS", "SpringBoot", ".NET"]
languages: ["typescript", "java", "c_sharp"]
YAML

cd /docgen
CLI_ARGS="local /github/workspace/${PATH_DIR}"
if [ -n "$API_DIR" ]; then
  CLI_ARGS="${CLI_ARGS} ${API_DIR}"
fi

uv run documentation-pipeline ${CLI_ARGS}
PIPELINE_EXIT=$?

if [ $PIPELINE_EXIT -eq 0 ]; then
  echo "## DocGen Documentation Pipeline — Success " >> "$GITHUB_STEP_SUMMARY"
else
  echo "## DocGen Documentation Pipeline — Failed " >> "$GITHUB_STEP_SUMMARY"
  exit $PIPELINE_EXIT
fi
