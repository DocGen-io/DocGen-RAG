"""
DocumentationCreator - Haystack component for generating REST API documentation.

This component analyzes code_mapper output, fetches dependency information from Weaviate,
and uses LLM to generate comprehensive API documentation in Postman and Swagger formats.
"""

from haystack import component
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from typing import Dict, Any, List, Optional
import json
import os
import logging
from string import Template

from src.utils.modelGenerator import ModelGenerator
from src.utils.json_loader import load_json_folder, load_json_file
from src.utils.weaviate_utils import fetch_by_method_name
from src.utils.llm_json_handler import LLMJsonHandler

logger = logging.getLogger(__name__)


DOCUMENTATION_PROMPT = Template("""### ROLE
You are a professional API documentation expert. You write comprehensive, accurate REST API documentation with examples, security considerations, and clear descriptions.

### TASK
Generate documentation for the following API endpoint based on the provided code context.

### REQUIREMENTS
Your documentation must include:
1. Each parameter, variable, and query parameter with its type
2. Description of each parameter's purpose
3. Complete endpoint description (what it does, expected behavior)
4. Example request and response
5. Clarification for any vague parameter names (indicate what ambiguous names mean)
6. Security concerns (authentication, authorization, rate limiting if applicable)
7. Types of all parameters

### API METHOD CONTEXT
Controller: $controller_name
Method: $method_name
HTTP Method: $http_method
Path: $endpoint_path
Base Path: $base_path

Method Definition:
$method_definition

### DEPENDENCY CONTEXT
The following are the internal service methods called by this endpoint:
$dependencies_context

### OUTPUT FORMAT
Return a JSON object with exactly two keys:
1. "postman": A valid Postman request object containing:
   - name, method, url, header, body (if applicable), description
2. "swagger": A valid OpenAPI 3.0 path operation object containing:
   - summary, description, parameters, requestBody (if applicable), responses, security

RETURN ONLY VALID JSON. NO MARKDOWN CODE BLOCKS. NO EXPLANATIONS.

### RESPONSE""")


@component
class DocumentationCreator:
    """
    Haystack component that generates REST API documentation from code analysis.
    
    Processes mapped_ast.json and AST files to create Postman and Swagger documentation
    for each API endpoint.
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        config_path: str = "config.yaml"
    ):
        self.generator = ModelGenerator("doc_creator", config_path).get_generator()
        self.config = self._load_config(config_path)
        self.output_dir = self.config.get("doc_creator", {}).get("output_dir", "output")
        
        # Initialize Weaviate document store
        self.document_store = WeaviateDocumentStore(url=weaviate_url)
    
    def _load_config(self, path: str) -> Dict[str, Any]:
        import yaml
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load config: {e}")
            return {}
    
    def _get_api_methods(self, mapped_ast: Dict) -> List[Dict]:
        """Filter methods where is_api_route=true from mapped_ast."""
        api_methods = []
        for class_name, class_data in mapped_ast.items():
            for method_info in class_data.get("methods", []):
                if method_info.get("is_api_route") is True:
                    api_methods.append({
                        "class_name": class_name,
                        "method_name": method_info.get("method"),
                        "dependencies": method_info.get("dependencies", [])
                    })
        logger.info(f"Found {len(api_methods)} API methods in mapped_ast")
        return api_methods
    
    def _get_dependencies_for_method(
        self,
        class_name: str,
        method_name: str,
        mapped_ast: Dict
    ) -> List[str]:
        """Get the list of dependencies for a method from mapped_ast."""
        class_data = mapped_ast.get(class_name, {})
        methods = class_data.get("methods", [])
        
        for method_info in methods:
            if method_info.get("method") == method_name:
                return method_info.get("dependencies", [])
        return []
    
    def _fetch_dependency_context(self, dependencies: List[str]) -> str:
        """Fetch dependency information from Weaviate and format as context."""
        if not dependencies:
            return "No internal dependencies identified."
        
        context_parts = []
        for dep in dependencies:
            # Extract method name from dependency (e.g., "postService.findAll" -> "findAll")
            parts = dep.split(".")
            method_name = parts[-1] if parts else dep
            
            # Fetch from Weaviate
            docs = fetch_by_method_name(self.document_store, method_name)
            
            if docs:
                doc = docs[0]
                context_parts.append(f"**{dep}**:\n{doc.content}\n")
            else:
                context_parts.append(f"**{dep}**: No additional context available.\n")
        
        return "\n".join(context_parts) if context_parts else "No dependency context found."
    
    def _build_prompt(self, method: Dict, dependencies_context: str) -> str:
        """Build the LLM prompt for documentation generation."""
        return DOCUMENTATION_PROMPT.substitute(
            controller_name=method.get("class_name", "Unknown"),
            method_name=method.get("method_name", "unknown"),
            http_method=method.get("method_type", "GET"),
            endpoint_path=method.get("method_path", "/"),
            base_path=method.get("base_path", "/"),
            method_definition=method.get("method_definition", ""),
            dependencies_context=dependencies_context
        )
    
    def _create_fallback_documentation(self, method: Dict) -> Dict:
        """Create a basic fallback documentation structure when LLM fails."""
        method_name = method.get("method_name", "unknown")
        http_method = method.get("method_type", "GET")
        path = method.get("method_path", "/")
        base_path = method.get("base_path", "/")
        full_path = f"{base_path.rstrip('/')}/{path.lstrip('/')}" if path else base_path
        
        return {
            "postman": {
                "name": method_name,
                "request": {
                    "method": http_method or "GET",
                    "header": [],
                    "url": {"raw": f"{{{{baseUrl}}}}{full_path}"}
                },
                "description": f"Auto-generated documentation for {method_name}. Manual review recommended."
            },
            "swagger": {
                "summary": method_name,
                "description": f"Endpoint: {method_name}. Documentation could not be fully generated.",
                "parameters": [],
                "responses": {
                    "200": {"description": "Success"},
                    "400": {"description": "Bad Request"},
                    "500": {"description": "Internal Server Error"}
                }
            }
        }
    
    def _generate_documentation(self, prompt: str, method: Dict) -> Optional[Dict]:
        """Call LLM to generate documentation and parse response with robust error handling."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = self.generator.run(prompt)["replies"][0]
                result = LLMJsonHandler.parse(response)
                
                # Validate structure
                if "postman" in result or "swagger" in result:
                    return result
                else:
                    logger.warning(f"Attempt {attempt + 1}: Missing postman/swagger keys, retrying...")
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Attempt {attempt + 1}: JSON parse error: {e}")
                if attempt < max_retries - 1:
                    continue
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}: Error: {e}")
                if attempt < max_retries - 1:
                    continue
        
        # All retries failed - use fallback
        logger.warning(f"Using fallback documentation for {method.get('method_name')}")
        return self._create_fallback_documentation(method)

    
    def _save_outputs(self, method_name: str, documentation: Dict) -> Dict[str, str]:
        """Save Postman and Swagger JSON files to output directory."""
        # Create method-specific output directory
        method_dir = os.path.join(self.output_dir, method_name)
        os.makedirs(method_dir, exist_ok=True)
        
        saved_files = {}
        
        # Save Postman JSON
        postman_data = documentation.get("postman", {})
        postman_path = os.path.join(method_dir, "postman.json")
        with open(postman_path, "w", encoding="utf-8") as f:
            json.dump(postman_data, f, indent=2)
        saved_files["postman"] = postman_path
        
        # Save Swagger JSON
        swagger_data = documentation.get("swagger", {})
        swagger_path = os.path.join(method_dir, "swagger.json")
        with open(swagger_path, "w", encoding="utf-8") as f:
            json.dump(swagger_data, f, indent=2)
        saved_files["swagger"] = swagger_path
        
        logger.info(f"Saved documentation for {method_name} to {method_dir}")
        return saved_files
    
    @component.output_types(
        methods_processed=int,
        methods_failed=int,
        output_files=Dict[str, Dict[str, str]]
    )
    def run(
        self,
        mapped_ast_path: str,
        ast_folder: str = None
    ) -> Dict[str, Any]:
        """
        Process mapped AST and generate API documentation.
        
        Args:
            mapped_ast_path: Path to mapped_ast.json file
            ast_folder: Optional, path to AST folder (used for additional context)
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting DocumentationCreator: mapped_ast={mapped_ast_path}")
        
        # Load mapped_ast
        mapped_ast = load_json_file(mapped_ast_path) or {}
        
        # Load AST data for additional context (method definitions, paths, etc.)
        ast_data = load_json_folder(ast_folder) if ast_folder else []
        
        # Build lookup for method details from AST
        method_details = {}
        for ast_file in ast_data:
            for file_data in ast_file.get("data", [ast_file]):
                for cls in (file_data if isinstance(file_data, list) else [file_data]):
                    class_name = cls.get("class_name", "")
                    base_path = cls.get("base_path", "/")
                    for method in cls.get("methods", []):
                        key = f"{class_name}.{method.get('method_name')}"
                        method_details[key] = {
                            "method_definition": method.get("method_definition", ""),
                            "method_type": method.get("method_type", "GET"),
                            "method_path": method.get("method_path", ""),
                            "base_path": base_path
                        }
        
        # Get API methods from mapped_ast
        api_methods = self._get_api_methods(mapped_ast)
        
        if not api_methods:
            logger.warning("No API methods found to document")
            return {
                "methods_processed": 0,
                "methods_failed": 0,
                "output_files": {}
            }
        
        methods_processed = 0
        methods_failed = 0
        output_files = {}
        
        for method in api_methods:
            method_name = method.get("method_name", "unknown")
            class_name = method.get("class_name", "Unknown")
            
            logger.info(f"Processing: {class_name}.{method_name}")
            
            try:
                # Get dependencies already included in method from _get_api_methods
                dependencies = method.get("dependencies", [])
                
                # Enrich method with details from AST
                key = f"{class_name}.{method_name}"
                if key in method_details:
                    method.update(method_details[key])
                
                # Fetch dependency context from Weaviate
                dep_context = self._fetch_dependency_context(dependencies)
                
                # Build prompt and generate documentation
                prompt = self._build_prompt(method, dep_context)
                documentation = self._generate_documentation(prompt, method)
                
                if documentation:
                    # Save output files
                    saved = self._save_outputs(method_name, documentation)
                    output_files[method_name] = saved
                    methods_processed += 1
                else:
                    logger.error(f"Failed to generate docs for {method_name}")
                    methods_failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing {class_name}.{method_name}: {e}")
                methods_failed += 1
        
        result = {
            "methods_processed": methods_processed,
            "methods_failed": methods_failed,
            "output_files": output_files
        }
        
        logger.info(f"DocumentationCreator complete: {methods_processed} processed, {methods_failed} failed")
        return result
