from haystack import component, Document
from typing import List
from src.utils.modelGenerator import ModelGenerator
from src.utils.llm_json_handler import LLMJsonHandler
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
        6. **JUST JSON FROMAT WITHOUT ANY TEXT**

        ### SCHEMA EXAMPLE
        Input:
        {
            "class_name": "AuthController",
            "methods": [
                { "method_definition": "public void login() { authService.verify(); }" }
            ]
        }

        ### Output:
        
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
            start_time = datetime.now()

            for ast_data in ast_data_list:
                query = ""

                query+=f"className: {ast_data['class_name']}\n"
                
                logger.info("Mapping data for class: ", ast_data['class_name'])
                
                # Build lookup for is_api_route per method
                api_route_lookup = {}
                defenitions = []
                for method in ast_data['methods']:
                    defenitions.append(method['method_definition'])
                    method_name = method.get('method_name', '')
                    api_route_lookup[method_name] = method.get('is_api_route', False)
                
                query+=f"methods: {defenitions}\n"

                # run the generator and get the first generated response
                full_prompt = prompt_template.substitute(query_data=query)
                response = self.generator.run(full_prompt)['replies'][0]

                # parse the response to json with repair and retry logic
                json_output = LLMJsonHandler.parse_with_retry(
                    response, 
                    generator=self.generator, 
                    prompt=full_prompt,
                    max_retries=2
                )

                # Merge is_api_route into each method's output
                for method_info in json_output.get('methods', []):
                    method_name = method_info.get('method', '')
                    method_info['is_api_route'] = api_route_lookup.get(method_name, False)

                output[ast_data['class_name']] = json_output
            
            end_time = datetime.now()
            
            logger.info(f"Mapping data for class: {ast_data['class_name']} took {end_time - start_time}")
        
        except Exception as e:
            logger.error(f"Failed to generate Code mapping: {e}")
            raise RuntimeError(f"Could not generate Code mapping.") from e

        return output


                


            