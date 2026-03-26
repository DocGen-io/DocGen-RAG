import os
import time
import concurrent.futures
from typing import List, Dict, Any
from haystack import component
from src.utils.logger import DocGenLogger
from src.utils.modelGenerator import ModelGenerator
import threading
from src.utils.config_loader import load_config
from src.utils.llm_json_handler import LLMJsonHandler
from prompts import file_analyzer_system_prompt, file_analyzer_user_prompt
from opentelemetry import context
import json

logger = DocGenLogger(__name__)


@component
class FilesAnalyzer:
    """
    Analyzes whole source files via LLM to extract internal dependencies.
    
    For each file, sends the numbered source code to the LLM which returns
    a list of methods/functions with their internal dependency mappings.
    Code splitting/chunking is handled separately by ASTCodeSplitter.
    
    Output is consumed by EndpointGraphManager to build/update dependency graphs.
    """

    def __init__(self, config_path: str = "config.yaml", max_workers: int = 5):
        self.max_workers = max_workers
        self.model_generator = ModelGenerator("code_analyzer", config_path).get_generator()
        self.config = load_config(config_path)

    @staticmethod
    def number_file_lines(file_path: str) -> List[str]:
        """Reads a file and returns a list of numbered lines."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [f"{i+1} | {line}" for i, line in enumerate(f)]
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return None

    def parallel_numbering(self, input_files: List[Dict[str, str]]) -> Dict[str, List[str]]:
        """Read and number lines for all input files in parallel."""
        results = {}
        start_time = time.time()

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self.number_file_lines, f['path']): f['path']
                for f in input_files
            }

            for future in concurrent.futures.as_completed(future_to_path):
                rel_path = future_to_path[future]
                try:
                    res = future.result()
                    if res is not None:
                        results[rel_path] = res
                except Exception as e:
                    logger.error(f"Thread error for {rel_path}: {e}")

        elapsed_time = time.time() - start_time
        logger.info(f"Processed {len(results)} files using {self.max_workers} threads in {elapsed_time:.2f} seconds.")

        return results

    def analyze_single_file(self, file_path: str, content: List[str]) -> Dict[str, Any]:
        """Analyzes a single file and returns the dependency extraction JSON output."""
        logger.info(f"Analyzing file: {file_path} with thread #{threading.get_ident()}")

        from haystack.dataclasses import ChatMessage
        content_str = "".join(content)
        user_prompt = file_analyzer_user_prompt.substitute(
            query_data_file_path=file_path,
            query_data_file_content=content_str
        )
        messages = [
            ChatMessage.from_system(file_analyzer_system_prompt),
            ChatMessage.from_user(user_prompt)
        ]

        # Get LLM response
        response = self.model_generator.run(messages=messages)['replies'][0]

        # Parse response
        json_output = LLMJsonHandler.parse_with_retry(
            response,
            generator=self.model_generator,
            prompt=messages,
            max_retries=2
        )

        return json_output

    def analyze_files(self, input_files: Dict[str, List[str]]) -> List[Dict[str, Any]]:
        """Analyze all files in parallel, extracting dependencies from each."""
        results = {}
        start_time = time.time()

        ctx = context.get_current()

        def wrapped_analyze(file_path, content, ctx):
            # Attach the parent context to this specific worker thread
            token = context.attach(ctx)
            try:
                return file_path, self.analyze_single_file(file_path, content)
            finally:
                context.detach(token)

        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for key, value in input_files.items():
                futures.append(executor.submit(wrapped_analyze, key, value, ctx))

            for future in concurrent.futures.as_completed(futures):
                try:
                    fp, result = future.result()
                    if result is not None:
                        result['file_path'] = fp
                        results[fp] = result
                        self._save_analyzer_output(fp, result)

                except Exception as e:
                    logger.error(f"Error analyzing file: {e}")

        elapsed = time.time() - start_time
        logger.info(f"Analyzed {len(results)} files in {elapsed:.2f}s")

        return list(results.values())

    def _save_analyzer_output(self, file_path: str, result: Dict[str, Any]) -> None:
        """Saves the analyzer output to a JSON file (if configured)."""
        output_path = self.config.get("code_analyzer", {}).get("analyzer_output_path")
        if output_path:
            try:
                file_name = os.path.basename(file_path)
                save_path = os.path.join(output_path, f"{file_name}.json")
                os.makedirs(output_path, exist_ok=True)

                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4)
                logger.info(f"Saved analyzer output to {save_path}")
            except Exception as e:
                logger.error(f"Failed to save analyzer output for {file_path}: {e}")

    @component.output_types(
        files=List[Dict[str, Any]],
    )
    def run(self, files: List[Dict[str, str]]):
        """
        Analyze files for internal dependencies.
        
        Args:
            files: List of file dicts from FileHasher (path, language, relative_path).
            
        Returns:
            files: List of dependency analysis results per file, each containing
                   file_path and content (list of methods with their dependencies).
        """
        # Number lines of each file (for LLM context)
        numbered = self.parallel_numbering(files)

        # Analyze files for dependencies via LLM
        results = self.analyze_files(numbered)

        return {"files": results}