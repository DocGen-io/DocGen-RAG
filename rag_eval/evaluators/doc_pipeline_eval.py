from ragas.metrics import faithfulness
from rag_eval.core.base_evaluator import BaseRagasEvaluator

class DocumentationPipelineEvaluator(BaseRagasEvaluator):
    """
    Evaluates the AST Parsing -> OpenAPI Generation Pipeline.
    Because this is an Information Extraction task, we primarily care about 'Faithfulness'
    (i.e., making sure the LLM didn't hallucinate endpoints that don't exist in the code context).
    """
    def get_metrics(self) -> list:
        return [
            # Did the Swagger documentation invent routes not in the source code chunks?
            faithfulness
        ]
