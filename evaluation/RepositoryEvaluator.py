import time
import os
import json
from typing import Optional, Dict

from src.pipelines.documentation_pipeline import DocumentationPipeline
from evaluation.metrics import evaluate_structural_validity, evaluate_accuracy
from src.utils.logger import DocGenLogger
from src.utils.types.evaluation_output_type import EvaluationRecord

logger = DocGenLogger(__name__)

class RepositoryEvaluator:
    """Handles the evaluation pipeline execution for a single repository"""
    
    def __init__(self, pipeline: DocumentationPipeline, model_name: str):
        self.pipeline = pipeline
        self.model_name = model_name

    def extract_project_name(self, repo_url: str) -> str:
        """Dynamically extracts a clean project name from standard and non-standard URLs."""
        clean_url = repo_url.rstrip("/")
        if clean_url.endswith(".git"):
            clean_url = clean_url[:-4]
        
        name = clean_url.split("/")[-1]
        
        # Fallback if the URL ends up with an empty name (e.g. malformed link)
        return name if name else f"repo_{int(time.time())}"

    def evaluate(self, repo_url: str, framework: str, language: str, ground_truth: Optional[Dict]) -> EvaluationRecord:
        start_time = time.time()
        project_name = self.extract_project_name(repo_url)
        
        logger.info(f"\n--- Evaluating {language} - {framework} ---", location="RepositoryEvaluator.evaluate")
        logger.info(f"Target: {repo_url}", location="RepositoryEvaluator.evaluate")
        
        error_msg = None
        structurally_valid = False
        acc_metrics = {}
        files_processed = 0

        try:
            pipeline_result = self.pipeline.run(source_type="git", path=repo_url)
            
            if pipeline_result.get("status") == "failed":
                error_msg = pipeline_result.get("error", "Unknown pipeline failure")
                logger.error(f"Pipeline failed for {repo_url}: {error_msg}", location="RepositoryEvaluator.evaluate")
            else:
                files_processed = pipeline_result.get("files", 0)
                output_dir = self.pipeline.config.get("doc_creator", {}).get("output_dir", "output") if hasattr(self.pipeline, "config") else "output"
                swagger_file = os.path.join(output_dir, project_name, "swagger.json")
                
                if os.path.exists(swagger_file):
                    with open(swagger_file, 'r') as f:
                        generated_swagger = json.load(f)
                    
                    structurally_valid = evaluate_structural_validity(generated_swagger)
                    
                    if ground_truth:
                        acc_metrics = evaluate_accuracy(generated_swagger, ground_truth)
                else:
                    error_msg = f"Pipeline completed but swagger.json not found at {swagger_file}"
                    
        except Exception as e:
            error_msg = f"Unhandled exception: {str(e)}"
            logger.error(f"Evaluating {repo_url} resulted in an exception: {e}", location="RepositoryEvaluator.evaluate")

        execution_time = time.time() - start_time
        
        return EvaluationRecord(
            model=self.model_name,
            language=language,
            framework=framework,
            repo_url=repo_url,
            success=(error_msg is None),
            execution_time_seconds=round(execution_time, 2),
            valid_openapi=structurally_valid,
            files_processed=files_processed,
            error=error_msg,
            **acc_metrics
        )
