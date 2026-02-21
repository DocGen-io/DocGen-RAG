import os
import time
import concurrent.futures
from typing import List, Dict,Any
from haystack import component
from src.utils.logger import DocGenLogger
from src.utils.modelGenerator import ModelGenerator
from string import Template
from src.utils.config_loader import load_config
import json
logger = DocGenLogger()

@component
class FilesAnalyzer:
    def __init__(self, max_workers: int = 5):
        # Allow the user to define thread count during initialization
        self.max_workers = max_workers
        self.model_generator = ModelGenerator("code_analyzer").get_generator()  
        self.config = load_config("config.yaml")

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
            You are a Static Code Analysis Engine specializing in Python and TypeScript. Your goal is to map function boundaries and internal call graphs.

        ### TASK
            Analyze the provided dictionary of file paths and source code. Identify all classes and functions, their line boundaries, and how they call each other internally.

        ### INPUT FORMAT
            A Dictionary: `{ "file_path": "lines_of_code_with_numbers" }`
        
        ### STRICT RULES
            1. OUTPUT ONLY RAW JSON. 
            2. NO PREAMBLE, NO POST-PROSE, AND NO MARKDOWN BLOCKS (```).
            3. THE RESPONSE MUST BEGIN WITH [ AND END WITH ].
            4. Ignore ALL files that are not used in creating the API (test files, config_files, etc.)

        ### EXTRACTION RULES
            1. **Scope:** Only include internal dependencies. Ignore external libraries (e.g., `os`, `requests`, `pandas`).
            2. **Dependency Types:**
            - `class-method`: A method calling another method within the same class (e.g., `self.helper()`).
            - `stand-alone`: A function calling another function, or a method calling a top-level function.
            3. **Priority:** Ensure all Data Transfer Objects (DTOs), Pydantic schemas, and data models are captured as high-priority nodes.
            4. **Accuracy:** `start_line` and `end_line` must be integers, not strings.

        ### OUTPUT GUARDS
            - **JSON ONLY.** Do not include markdown code blocks (```json), preamble, or post-prose.
            - Return a flat list of objects.
            - If no dependencies exist, return an empty list `[]` for that key.

        ### JSON SCHEMA
      { 
        "file_path": "str",

       "content": [
            {
                "type": "class | function | schema",
                "name": "str",
                "start_line": int,
                "end_line": int,
                "dependencies": [
                    {
                        "dependency_name": "str",
                        "dependency_type": "stand-alone | class-method"
                    }
                ]
            }
        ]
      }

        ### DATA TO ANALYZE
        $query_data_file_path
        $query_data_file_content
         """)

        for key, value in input_files.items():
            logger.info(f"Analyzing file: {key}")
            
            # 1. Prepare query
            content_str = "".join(value)
            query = prompt.substitute(query_data_file_path=key, query_data_file_content=content_str)
            
            # 2. Get LLM response
            response = self.model_generator.run(query)['replies'][0]

            try:
                # 3. CONVERT STRING TO JSON (The key fix)
                # This turns the "string" into a real Python list/dict
                structured_data = json.loads(response)
                
                # If LLM wraps it in an extra list [[]], take the first element
                if isinstance(structured_data, list) and len(structured_data) > 0:
                    if isinstance(structured_data[0], list):
                        structured_data = structured_data[0]
                
                results[key] = structured_data
            except Exception as e:
                logger.error(f"Could not parse JSON for {key}: {e}")
                results[key] = {"error": "parsing_failed", "raw": response}

            # 4. SAVE TO INDIVIDUAL FILE
            os.makedirs("analyzer_output", exist_ok=True)
            # Safe way to get filename (e.g., 'app.ts' from 'src/app.ts')
            clean_filename = os.path.basename(key) 
            
            with open(f"analyzer_output/{clean_filename}.json", "w", encoding='utf-8') as f:
                # Saving the structured_data makes it a real JSON file
                json.dump(results[key], f, indent=4)

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
        

    