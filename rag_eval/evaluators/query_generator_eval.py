import pandas as pd
from rag_eval.core.base_evaluator import BaseRagasEvaluator

class QueryGeneratorEvaluator(BaseRagasEvaluator):
    """
    Evaluates the LLM Query Generation (Translating user text to Weaviate queries).
    Ragas standard metrics are built for Q&A, so for query translation 
    we implement a simple exact match / substring semantic evaluation, but keep
    the same unified Interface and CSV output as the core Ragas framework.
    """
    def get_metrics(self) -> list:
        # Not using standard Ragas LLM metrics here, handling logic in evaluate_pipeline overrides
        return []

    def evaluate_pipeline(self, data: list[dict], run_name: str) -> pd.DataFrame:
        """
        Overrides the base evaluation to use simpler translation metrics.
        Data format: [{"question": "User text", "answer": "Generated query", "ground_truth": "Expected query"}]
        """

        print(f"Starting simple evaluation for: {run_name} (Query Translation)...")
        results = []
        
        for item in data:
            generated = str(item.get("answer", "")).lower().strip()
            expected = str(item.get("ground_truth", "")).lower().strip()
            
            # Simple metrics for query generation
            exact_match = int(generated == expected)
            is_subset = int(expected in generated) # In case LLM generated extra whitespace/wrappers
            
            # Could easily add Levenshtein distance or small local Embedding similarity here
            
            results.append({
                "question": item.get("question"),
                "generated_query": generated,
                "expected_query": expected,
                "exact_match": exact_match,
                "is_subset_match": max(exact_match, is_subset)
            })
            
        df = pd.DataFrame(results)
        
        # Calculate summary metrics
        exact_match_score = df["exact_match"].mean()
        subset_score = df["is_subset_match"].mean()
        
        # Export
        csv_filename = f"{run_name}_simple_evaluation.csv"
        df.to_csv(csv_filename, index=False)
        print(f"Evaluation complete! Detailed report saved to: {csv_filename}")
        
        print("\n--- High Level Summary ---")
        print(f"Exact Match Accuracy: {exact_match_score:.4f}")
        print(f"Subset Match Accuracy: {subset_score:.4f}")
        
        return df
