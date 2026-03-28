import time
import json
import os
import requests
import pandas as pd
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from src.pipelines.documentation_pipeline import DocumentationPipeline
from evaluation.metrics import evaluate_structural_validity, evaluate_accuracy
from src.utils.logger import DocGenLogger
from src.utils.types.evaluation_output_type import EvaluationRecord
from evaluation.GroundTruthManager import GroundTruthManager
from evaluation.RepositoryEvaluator import RepositoryEvaluator

logger = DocGenLogger(__name__)


class EvaluationOrchestrator:
    """Coordinates reading repositories, running the evaluation, and writing results"""
    
    def __init__(self, repositories_file: str, output_file: str, model_name: str, description: str = ""):
        self.repositories_file = repositories_file
        self.output_file = output_file
        self.ground_truth_manager = GroundTruthManager()
        self.description = description
        
        # Load historical results ONCE so we don't exponentially duplicate rows during save_results
        if os.path.exists(self.output_file):
            self.historical_df = pd.read_csv(self.output_file)
        else:
            self.historical_df = None
        self.evaluator = RepositoryEvaluator(
            pipeline=DocumentationPipeline(config_path="config.yaml"), 
            model_name=model_name
        )
        self.results: List[EvaluationRecord] = []

    def load_repositories(self) -> List[Dict]:
        with open(self.repositories_file, 'r') as f:
            return json.load(f)

    def save_results(self):
        records = [asdict(r) for r in self.results]
        df = pd.DataFrame(records)
        if self.description:
            df["description"] = self.description
            
        if self.historical_df is not None:
            df = pd.concat([self.historical_df, df], ignore_index=True)
            
        df.to_csv(self.output_file, index=False)
        logger.info(f"Progress iteratively saved to {self.output_file}", location="EvaluationOrchestrator.save_results")

    def run(self):
        repos_data = self.load_repositories()
        
        for lang_group in repos_data:
            language = lang_group.get("language", "Unknown")
            
            # The JSON might use `ground_truth_url` or `api_documentation_url`
            gt_url = lang_group.get("ground_truth_url") or lang_group.get("api_documentation_url")
            ground_truth = self.ground_truth_manager.get_ground_truth(gt_url, language)
            
            for repo_info in lang_group.get("repos", []):
                # Handle varying keys mapped in JSON ('repo_url', 'url', 'repo')
                repo_url = repo_info.get("repo_url") or repo_info.get("url") or repo_info.get("repo")
                framework = repo_info.get("uses", "Unknown")
                
                if not repo_url:
                    logger.warning(f"Repository entry skipped due to missing URL: {repo_info}", location="EvaluationOrchestrator.run")
                    continue
                    
                record = self.evaluator.evaluate(repo_url, framework, language, ground_truth)
                self.results.append(record)
                self.save_results()

        logger.info(f"\n=== Evaluation Complete! Final results at {self.output_file} ===", location="EvaluationOrchestrator.run")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run automated thesis evaluation harness")
    parser.add_argument("--model", type=str, default="llama3", help="Name of the model being evaluated")
    parser.add_argument("--config", type=str, default="evaluation/repositories.json", help="Path to repositories JSON configuration")
    parser.add_argument("--output", type=str, default="evaluation/data/evaluation_results.csv", help="Output file path for evaluation metrics CSV")
    parser.add_argument("--description", type=str, default="", help="Description of the evaluation")
    args = parser.parse_args()
    
    orchestrator = EvaluationOrchestrator(
        repositories_file=args.config,
        output_file=args.output,
        model_name=args.model,
        description=args.description
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
