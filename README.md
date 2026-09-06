# DocGen-RAG

M.Sc. thesis component: Haystack 2.0 pipelines, Tree-sitter extractors, CLI, and evaluation.

Turns NestJS / Spring Boot / ASP.NET REST source into OpenAPI 3.0 fragments, then a RAG pipeline retrieves code context and a merger builds a spec.

HTTP console is **[DocGen-API](https://github.com/DocGen-io/DocGen-API)** + **[DocGen-UI](https://github.com/DocGen-io/DocGen-UI)**. This repo is not a public HTTP API and not a hosted product.

Org: [github.com/DocGen-io](https://github.com/DocGen-io) · site: [ali-hasan.me/projects/docgen](https://ali-hasan.me/projects/docgen)

## What this is / is not

**Is**

- CLI + Haystack 2.0 pipelines + Weaviate index
- Tree-sitter `.scm` extractors for **TypeScript, Java, and C#** only (`queries/`)
- Evaluation on 8 RealWorld / Conduit-style repos

**Is not**

- Extractors for Python, Go, or PHP
- A public multi-tenant SaaS or a production URL
- Native Weaviate hybrid search (retrieval concatenates dense + BM25)
- SAST / security scanning
- Graph-aware incremental rebuilds (unchanged files are skipped by **file hash** only)

Paid work on the CV is NestJS / Next.js / PostgreSQL. DocGen is the thesis product.

## Run

Python 3.10+. Live config is **`config.yaml`**, not `settings.yml`.

```bash
git clone https://github.com/DocGen-io/DocGen-RAG.git
cd DocGen-RAG
uv sync --extra cli
uv run docgen
uv run pytest tests/ -q
```

Needs a Weaviate URL (compose in the API repo, or your own). LLM keys as in `config.yaml` (Gemini / Ollama / OpenAI).

There is no `src.api.main` in this package.

## Evaluation

```bash
uv run python evaluation/evaluate.py
```

Suffix match vs ground truth. Completeness can exceed 1. σ(method F1) ≈ 0.23. Express + Drizzle path extraction is weak. Do not quote 90–100% precision.

| Model | Method F1 | Path F1 | Time (s) | Valid OpenAPI | Completeness |
|-------|-----------|---------|----------|---------------|--------------|
| gemini-2.5-flash-lite | 0.818 | 0.836 | 110 | 88% | 1.09 |
| gemini-2.5-pro | 0.821 | 0.846 | 862 | 88% | 1.09 |
| gemini-2.5-flash | 0.755 | 0.792 | 415 | 100% | 0.96 |

Lite vs Pro ≈ **7.8×** faster at similar method F1.

## Layout

```
cli/           uv run docgen
src/           Haystack components and pipelines
queries/       Tree-sitter .scm (TS, Java, C#)
evaluation/    ground truths + evaluate.py
prompts/       LLM prompts
config.yaml    live provider config
```

## Related

- [DocGen-API](https://github.com/DocGen-io/DocGen-API) — FastAPI + **Celery** worker
- [DocGen-UI](https://github.com/DocGen-io/DocGen-UI)
- [DocGen-Action](https://github.com/DocGen-io/DocGen-Action) — needs a **persistent** Weaviate URL

Ali Saleem Hasan — [ali-hasan.me](https://ali-hasan.me)
