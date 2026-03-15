import os
import time
import concurrent.futures
from typing import List, Dict,Any
from haystack import component
from src.utils.logger import DocGenLogger
from src.utils.modelGenerator import ModelGenerator
from string import Template
import threading
from src.utils.config_loader import load_config
from src.utils.llm_json_handler import LLMJsonHandler
from prompts import file_analyzer_system_prompt, file_analyzer_user_prompt
from opentelemetry import context
import json
logger = DocGenLogger()

@component
class FilesAnalyzer:
    def __init__(self, max_workers: int = 5):
        self.max_workers = max_workers
        self.model_generator = ModelGenerator("code_analyzer", temperature=0.0, seed=42).get_generator()  
        self.config = load_config("config.yaml")
        self.llm_json_handler = LLMJsonHandler()

    @staticmethod
    def number_file_lines(file_path: str) -> List[str]:
        """Reads a file and returns a list of numbered lines."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [f"{i+1} | {line}" for i, line in enumerate(f)]
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return None


    def parallel_numbering(self, input_files: List[Dict[str, str]])-> Dict[str, List[str]]:
        
        results = {}
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit using absolute path, but keep relative path for the result key
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
    
        end_time = time.time()
        elapsed_time = end_time - start_time
        logger.info(f"Processed {len(results)} files using {self.max_workers} threads in {elapsed_time:.2f} seconds.")
        
        return results


    def analyze_single_file(self, file_path: str, content: List[str]) -> Dict[str, Any]:
        """Analyzes a single file and returns the structured JSON output."""
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
        
        # 2. Get LLM response
        response = self.model_generator.run(messages=messages)['replies'][0]
        
        # 3. Parse response
        json_output = LLMJsonHandler.parse_with_retry(
            response, 
            generator=self.model_generator, 
            prompt=messages,
            max_retries=2
        )
        
        return json_output

    def analyze_files(self, input_files: Dict[str, List[str]])-> List[Dict[str,Any]]:
        results = {}
        start_time = time.time()

        ctx = context.get_current()


        def wrapped_analyze(file_path, content, ctx):
            # Attach the parent context to this specific worker thread
            token = context.attach(ctx)
            try:
                return file_path, self.analyze_single_file(file_path, content)
            finally:
                # detach to prevent memory leaks in the thread pool
                context.detach(token)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            for key, value in input_files.items():
                futures.append(executor.submit(wrapped_analyze, key, value, ctx))
            
            for future in concurrent.futures.as_completed(futures):
                try:
                    fp, result = future.result()
                    if result is not None:
                        # Ensure the file_path key also is in the dictionary just in case
                        result['file_path'] = fp
                        results[fp] = result
                        
                        # Inject exact lines into every item in 'content'
                        if 'content' in result and isinstance(result['content'], list):
                            for item in result['content']:
                                start_line = item.get('start_line')
                                end_line = item.get('end_line')
                                item['lines'] = self.get_exact_lines(fp, start_line, end_line)

                        # if no content (data-model or interface)
                        else:
                            
                            result['lines'] = self.get_exact_lines(fp, result.get('start_line'), result.get('end_line'))
                            

                        self._save_analyzer_output(fp, result)

                except Exception as e:
                    logger.error(f"Error analyzing file: {e}")
        
        end_time = time.time()
        logger.info(f"Analyzed {len(results)} files in {end_time - start_time:.2f}s")
        
        return list(results.values())
      
    
    def _save_analyzer_output(self, file_path: str, result: Dict[str, Any]) -> None:
        """Saves the analyzer output to a JSON file."""
        output_path = self.config.get("code_analyzer", {}).get("analyzer_output_path")
        if output_path:
            try:
                # Keep the original filename structure and save it out as JSON
                file_name = os.path.basename(file_path)
                save_path = os.path.join(output_path, f"{file_name}.json")
                os.makedirs(output_path, exist_ok=True)
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=4)
                logger.info(f"Saved analyzer output to {save_path}")
            except Exception as e:
                logger.error(f"Failed to save analyzer output for {file_path}: {e}")



    # get exact lines from files using start_line and end_line
    def get_exact_lines(self, file_path: str, start_line: int, end_line: int) -> List[str]:
        """Gets exact lines from a file using start_line and end_line."""
        if start_line is None or end_line is None:
            return None
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line for i, line in enumerate(f) if start_line <= i+1 <= end_line]
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            return None
        
    @component.output_types(
       files=List[Dict[str, Any]],
    )
    def run(self, files: List[Dict[str, str]]):
        

        # first number lines of file
        results =  self.parallel_numbering(files)

        # then analyze the files
        results = self.analyze_files(results)

        return {"files":results}

        # then provide the whole file with line numbers as input to llm
        # llm will provide the line ranges for each function
        

    