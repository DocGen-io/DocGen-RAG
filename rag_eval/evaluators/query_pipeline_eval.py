from ragas.metrics import faithfulness, answer_relevancy, context_precision, context_recall
from rag_eval.core.base_evaluator import BaseRagasEvaluator

class QueryPipelineEvaluator(BaseRagasEvaluator):
    """
    Evaluates the standard RAG Query Pipeline (Hybrid Search + LLM Generation).
    Uses the full "RAG Triad" to measure both retrieval quality and generation accuracy.
    """
    def get_metrics(self) -> list:
        return [
            # Evaluates Retrieval: Were the most important files ranked at the top?
            context_precision,
            
            # Evaluates Retrieval: Did the DB fetch all the facts needed to form the ground_truth?
            context_recall
        ]
