"""
Base evaluator for Ragas.
Handles Dataset conversion and CSV export. Child classes define metrics.
"""
import warnings
from abc import ABC, abstractmethod
import pandas as pd
from datasets import Dataset
from ragas import evaluate


class BaseRagasEvaluator(ABC):
    """Standard interface for all Ragas evaluators."""

    @abstractmethod
    def get_metrics(self) -> list:
        """Returns the Ragas metrics for this pipeline type."""
        ...

    def evaluate_pipeline(
        self, data: list[dict], run_name: str, llm=None, embeddings=None
    ) -> pd.DataFrame:
        """Run Ragas evaluation with Langchain models, print summary, save CSV."""
        dataset = Dataset.from_list(data)
        metrics = self.get_metrics()

        print(f"Starting evaluation: {run_name} ({len(metrics)} metrics)...")

        # Langchain models integrate natively with evaluate() without any complexity
        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=llm,
            embeddings=embeddings,
        )

        df = result.to_pandas()
        csv_path = f"{run_name}_ragas_evaluation.csv"
        df.to_csv(csv_path, index=False)

        print(f" Saved to: {csv_path}")
        self._print_summary(result)
        return df

    @staticmethod
    def _print_summary(result):
        """Print averaged metric scores from Ragas EvaluationResult."""
        print("\n--- Summary ---")
        try:
            scores = result.scores
            if scores:
                avg = {}
                for row in scores:
                    for k, v in row.items():
                        avg.setdefault(k, []).append(float(v) if v is not None else 0.0)
                for k, vals in avg.items():
                    print(f"  {k}: {sum(vals)/len(vals):.4f}")
        except Exception as e:
            print(f"Failed to generate summary: {e}")
