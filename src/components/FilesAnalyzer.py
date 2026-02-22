import os
import time
import concurrent.futures
from typing import List, Dict,Any
from haystack import component
from src.utils.logger import DocGenLogger
from src.utils.modelGenerator import ModelGenerator
from string import Template
from src.utils.config_loader import load_config
from src.utils.llm_json_handler import LLMJsonHandler
import json
logger = DocGenLogger()

@component
class FilesAnalyzer:
    def __init__(self, max_workers: int = 5):
        # Allow the user to define thread count during initialization
        self.max_workers = max_workers
        self.model_generator = ModelGenerator("code_analyzer").get_generator()  
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
                executor.submit(self.number_file_lines, f['path']): f['relative_path'] 
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


    def analyze_files(self, input_files: Dict[str, List[str]])-> Dict[str, Dict[str,Any]]:
        results = {}
        start_time = time.time()
        prompt = Template("""
        ### ROLE
        You are a Static Code Analysis Engine. Your goal is to map function boundaries, internal call graphs, and API endpoints.

        ### TASK
        Analyze the provided file path and source code. Identify all classes, functions, and schemas. 
        For every method, determine if it is an API endpoint (e.g., has decorators like @Get, @Post, @app.get, etc.).

        ### STRICT RULES
        1. OUTPUT ONLY RAW JSON. No markdown backticks, no preamble.
        2. If a method is NOT an API endpoint, set "is_api_method" to null.
        3. "start_line" and "end_line" MUST be integers.

        ### JSON SCHEMA STRUCTURE
        { 
            "file_path": "str",
            "content": [
                {
                    "type": "class | function | schema",
                    "name": "str",
                    "start_line": int,
                    "end_line": int,
                    "is_api_method": {
                        "method_type": "get | post | put | delete | patch",
                        "path": "str"
                    }, 
                    "dependencies": [
                        {
                            "dependency_name": "str",
                            "dependency_type": "stand-alone | class-method"
                        }
                    ]
                }
            ]
        }

        ### EXTRACTION RULES
        - **API Detection:** If you see decorators (like `@Get('/')` or `@route`) or framework-specific routing, fill the "is_api_method" object. Otherwise, set it to null.
        - **Internal Only:** Ignore external libraries (e.g., os, requests).
        - **Data Shapes:** Prioritize DTOs, Schemas, and Models.

        ### DATA TO ANALYZE
        Path: $query_data_file_path
        Content:
        $query_data_file_content
        """)

        for key, value in input_files.items():
            logger.info(f"Analyzing file: {key}")
            
            # 1. Prepare query
            content_str = "".join(value)
            query = prompt.substitute(query_data_file_path=key, query_data_file_content=content_str)
            
            # 2. Get LLM response
            response = self.model_generator.run(query)['replies'][0]

            
            # 4. SAVE TO INDIVIDUAL FILE
            os.makedirs("analyzer_output", exist_ok=True)
            # Safe way to get filename (e.g., 'app.ts' from 'src/app.ts')
            clean_filename = os.path.basename(key) 
            
            json_output = LLMJsonHandler.parse_with_retry(
                    response, 
                    generator=self.model_generator, 
                    prompt=query,
                    max_retries=2
                )
            if json_output is not None:
                with open(f"analyzer_output/{clean_filename}.json", "w", encoding='utf-8') as f:
                    # Saving the structured_data makes it a real JSON file
                    
                    json.dump(json_output, f, indent=4)

        logger.info(f"Analyzed {len(results)} files in {time.time() - start_time:.2f}s")
        return results

        

        
    @component.output_types(
       files=List[Dict[str, List[str]]],
    )
    def run(self, input_files: List[Dict[str, str]]):
        

        # first number lines of file
        results =  self.parallel_numbering(input_files)

        # then analyze the files
        results = self.analyze_files(results)

        return {"files":results}

        # then provide the whole file with line numbers as input to llm
        # llm will provide the line ranges for each function
        

    