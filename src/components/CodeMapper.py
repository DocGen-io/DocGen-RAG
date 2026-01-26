from haystack import component, Document
from typing import List
from src.utils.modelGenerator import ModelGenerator 
import json
import logging
from string import Template
from datetime import datetime

logger = logging.getLogger(__name__)

@component
class CodeMapper:

    """
        Check out methods dependencies and map them to each other
        input: ast_data_list
        output: mapped_ast_data_list

        This will use a small LLM to check out methods dependencies and map them to each other

    """


    def __init__(self):
       self.generator = ModelGenerator("code_mapper").get_generator()

    @component.output_types(mapped_ast_data_list=dict)
    def run(self, ast_data_list: List[dict]):
        all_docs = []
        prompt_template = Template("""### ROLE
        You are a Static Code Analysis Engine. Your task is to identify internal method dependencies within a given class.

        ### TASK
        Analyze the provided JSON input containing a class name and method definitions. Map each method to the internal services or methods it calls.

        ### CONSTRAINTS
        1. **Dependencies Only**: List only internal service calls (e.g., `service.method`).
        2. **Exclude External Libraries**: Do not include calls to standard libraries or third-party utilities (e.g., bcrypt, math, lodash, or native language APIs).
        3. **Internal Context**: If a method is called on `this` or `self`, include it.
        4. **Strict Output**: Return ONLY a raw JSON object. 
        5. **No Markdown**: Do not wrap the output in ```json blocks. Do not include any conversational text, explanations, or notes.

        ### SCHEMA EXAMPLE
        Input:
        {
            "class_name": "AuthController",
            "methods": [
                { "method_definition": "public void login() { authService.verify(); }" }
            ]
        }

        Output:
        {
            "methods": [
                {
                    "method": "login",
                    "dependencies": ["authService.verify"]
                }
            ]
        }

        ### DATA TO ANALYZE
        $query_data

        ### RESPONSE""")

        try:

            output = {}
            query = ""
            start_time = datetime.now()

            for ast_data in ast_data_list:
                query+=f"className: {ast_data['class_name']}\n"
                
                logger.info("Mapping data for class: ", ast_data['class_name'])
                # add method defenitions to the query
                defenitions = []
                for method in ast_data['methods']:
                    defenitions.append(method['method_definition'])
                
                query+=f"methods: {defenitions}\n"

                # run the generator and get the first generated response
                response = self.generator.run(prompt_template.substitute(query_data=query))['replies'][0]

                # parse the response to json
                json_output = json.loads(response)

                output[ast_data['class_name']] = json_output
            
            end_time = datetime.now()
            
            logger.info(f"Mapping data for class: {ast_data['class_name']} took {end_time - start_time}")
        
        except Exception as e:
            logger.error(f"Failed to generate Code mapping: {e}")
            raise RuntimeError(f"Could not generate Code mapping.") from e

        return output


                


            