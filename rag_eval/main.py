"""
DocGen-RAG Evaluation Suite — Ragas 0.4 Native.

Runs the live RAG pipeline against ground-truth data,
grades with native Ragas LLM/Embedding providers (Vertex AI or Ollama).
Zero custom wrappers. Zero Langchain. Zero deprecation warnings.

Usage:
    uv run python rag_eval/main.py --pipeline query --judge vertex
    uv run python rag_eval/main.py --pipeline querygen --judge vertex
"""
import sys
import os
import argparse
import json
import warnings
from src.utils.json_loader import load_json_file
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Resolve imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rag_eval.core.judge_factory import JudgeFactory
from rag_eval.evaluators.query_pipeline_eval import QueryPipelineEvaluator
from rag_eval.evaluators.doc_pipeline_eval import DocumentationPipelineEvaluator
from rag_eval.evaluators.query_generator_eval import QueryGeneratorEvaluator
from src.pipelines.query_pipeline import QueryPipeline






def build_live_query_data(limit: int = 10, gt_path: str = "evaluation/ground_truths/query_pipeline_gt.json") -> list[dict]:
    """
    Execute the real QueryPipeline against Weaviate for each ground-truth question.
    Returns Ragas-format dicts: {question, contexts, answer, ground_truth}.
    """

    gt = load_json_file(gt_path)
    pipeline = QueryPipeline()
    limit = min(limit, len(gt))

    print(f"Running {limit} live queries through QueryPipeline...")
    data = []
    for i, item in enumerate(gt[:limit]):
        q = item["question"]
        project = item.get("project_name", "Dartsee")
        print(f"  [{i+1}/{limit}] {q} (Project: {project})")
        results = pipeline.run(query=q, project_name=project)

        contexts = [
            f"{r.get('content', '')} {r.get('summary', '')}".strip()
            for r in results
        ] or ["No relevant endpoints found."]

        # Stringify ground_truth gracefully if it's our new list of dicts (for Semantic Precision maps)
        # to ensure Ragas LLM evaluators can read them properly.
        raw_gt = item.get("ground_truth", "")
        if isinstance(raw_gt, list):
            if all(isinstance(x, dict) for x in raw_gt):
                str_gt = "\n".join([f"{x.get('method', 'GET').upper()} {x.get('path', '')}: {x.get('summary', '')}" for x in raw_gt])
            else:
                str_gt = " ".join(str(x) for x in raw_gt)
        else:
            str_gt = str(raw_gt)

        data.append({
            "question": q,
            "contexts": contexts,
            "answer": item.get("answer", str_gt),
            "ground_truth": str_gt,
        })
    return data


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="DocGen-RAG Evaluation Suite (Ragas 0.4)")
    parser.add_argument("--judge", choices=["vertex", "ollama"], default="vertex")
    parser.add_argument("--pipeline", choices=["query", "docgen", "querygen", "all"], default="all")
    parser.add_argument("--limit", type=int, default=10, help="Max questions for live query eval")
    parser.add_argument("--gt_path", type=str, default="evaluation/ground_truths/query_pipeline_gt.json", help="Path to ground truth JSON")
    args = parser.parse_args()

    # 1. Initialize native Ragas judge
    try:
        if args.judge == "vertex":
            llm, embeddings = JudgeFactory.get_vertex_ai_judge()
        else:
            llm, embeddings = JudgeFactory.get_ollama_judge()
    except Exception as e:
        print(f" Judge init failed: {e}")
        sys.exit(1)

    print(f"\n{'='*50}")
    print(f"Evaluation Suite — Judge: {args.judge.upper()}")
    print(f"{'='*50}")

    # 2. Query Pipeline (live retrieval + ground truth)
    if args.pipeline in ("query", "all"):
        print("\n--- Query Pipeline ---")
        QueryPipelineEvaluator().evaluate_pipeline(
            data=build_live_query_data(limit=args.limit),
            run_name="query_pipeline",
            llm=llm,
            embeddings=embeddings,
        )

    # 3. Documentation Pipeline
    if args.pipeline in ("docgen", "all"):
        print("\n--- Documentation Pipeline ---")
        DocumentationPipelineEvaluator().evaluate_pipeline(
            data=[],
            run_name="doc_pipeline",
            llm=llm,
            embeddings=embeddings,
        )

    # 4. Query Generation (simple exact-match, no LLM needed)
    if args.pipeline in ("querygen", "all"):
        print("\n--- Query Generation Pipeline ---")
        QueryGeneratorEvaluator().evaluate_pipeline(
            data=load_json_file(args.gt_path),
            run_name="querygen_pipeline",
        )

    print("\n All evaluations complete. Check the CSV files.")


if __name__ == "__main__":
    main()
