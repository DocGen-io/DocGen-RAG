"""
DocumentationCreator - Haystack component for generating REST API documentation.

This component analyzes code_mapper output, fetches dependency information from Weaviate,
and uses LLM to generate comprehensive API documentation in Swagger formats.
"""

import os
import json
from string import Template
from haystack import component
from src.utils.logger import DocGenLogger
from typing import Dict, Any, List, Optional
from src.utils.config_loader import load_config
from src.utils.llm_json_handler import LLMJsonHandler
from src.utils.weaviate_utils import fetch_by_node_id
from src.utils.dependency_graph import DependencyGraph
from src.utils.modelGenerator import ModelGenerator
from prompts import doc_creator_prompt as DOCUMENTATION_PROMPT
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
logger = DocGenLogger(__name__)


@component
class DocumentationCreator:
    """
    Haystack component that generates REST API documentation from code analysis.
    
    Processes mapped_ast.json and AST files to create Swagger documentation
    for each API endpoint.
    """
    
    def __init__(
        self,
        weaviate_url: str = "http://127.0.0.1:8080",
        config_path: str = "config.yaml"
    ):
        self.generator = ModelGenerator("doc_creator", config_path).get_generator()
        self.config = load_config(config_path)
        self.output_dir = self.config.get("doc_creator", {}).get("output_dir", "output")
        
        # Initialize Weaviate document store
        self.document_store = WeaviateDocumentStore(url=weaviate_url)
    
    def _fetch_dependency_context(self, node_ids: List[str]) -> str:
        """Fetch code context from Weaviate for a list of node IDs."""
        if not node_ids:
            return "No internal dependencies identified."
        
        context_parts = []
        for node_id in node_ids:
            # Fetch from Weaviate using composite ID
            docs = fetch_by_node_id(self.document_store, node_id)
            
            if docs:
                doc = docs[0]
                context_parts.append(f"**{node_id}**:\n{doc.content}\n")
            else:
                context_parts.append(f"**{node_id}**: No additional context available.\n")
        
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
                
                if  "swagger" in result:
                    return result
                else:
                    logger.warning(f"Attempt {attempt + 1}: Missing swagger keys, retrying...")
                    
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
        """Save Swagger JSON files to output directory."""
        # Create method-specific output directory
        method_dir = os.path.join(self.output_dir, method_name)
        os.makedirs(method_dir, exist_ok=True)
        
        saved_files = {}
        
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
        output_files=Dict[str, Dict[str, str]],
        output_dir=str
    )
    def run(
        self,
        endpoint_graphs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process EndpointGraphs, fetch code context, and generate API documentation.
        
        Args:
            endpoint_graphs: Dictionary mapping endpoint_id to DependencyGraph objects
            
        Returns:
            Dictionary with processing results
        """
        logger.info(f"Starting DocumentationCreator")
        
        if not endpoint_graphs:
            logger.warning("No endpoint graphs found to document")
            return {
                "methods_processed": 0,
                "methods_failed": 0,
                "output_files": {},
                "output_dir": self.output_dir
            }
        
        methods_processed = 0
        methods_failed = 0
        output_files = {}
        
        for endpoint_id, graph in endpoint_graphs.items():
            logger.info(f"Processing endpoint graph: {endpoint_id}")
            
            try:
                # 1. Gather all nodes involved in this endpoint (including the endpoint itself)
                node_ids = list(graph.get_all_nodes())
                
                # 2. Fetch context from Weaviate for all nodes
                dep_context = self._fetch_dependency_context(node_ids)
                
                # 3. Extract the endpoint method's details from Weaviate to guide the prompt
                endpoint_doc_list = fetch_by_node_id(self.document_store, endpoint_id)
                if not endpoint_doc_list:
                    logger.error(f"Endpoint {endpoint_id} not found in Weaviate. Skipping.")
                    methods_failed += 1
                    continue
                    
                endpoint_doc = endpoint_doc_list[0]
                meta = endpoint_doc.meta
                
                api_details_str = meta.get("api_method_details", "{}")
                try:
                    if isinstance(api_details_str, str):
                        api_details = json.loads(api_details_str)
                    else:
                        api_details = api_details_str
                except Exception:
                    api_details = {}
                
                if not isinstance(api_details, dict):
                    api_details = {}
                    
                method_info = {
                    "class_name": meta.get("class_name", endpoint_id.split(":")[1] if len(endpoint_id.split(":")) > 1 else "Unknown"),
                    "method_name": meta.get("name", endpoint_id.split(":")[2] if len(endpoint_id.split(":")) > 2 else "unknown"),
                    "method_type": api_details.get("method_type", "GET"),
                    "method_path": api_details.get("method_path", "/"),
                    "base_path": api_details.get("base_path", "/"),
                    "method_definition": endpoint_doc.content
                }
                
                # 4. Build prompt and generate
                prompt = self._build_prompt(method_info, dep_context)
                documentation = LLMJsonHandler.parse_with_retry(generator=self.generator, prompt=prompt,max_retries=3)
                
                if documentation:
                    method_name = method_info.get("method_name", "unknown")
                    # Save output files
                    saved = self._save_outputs(method_name, documentation)
                    output_files[method_name] = saved
                    methods_processed += 1
                else:
                    logger.error(f"Failed to generate docs for {endpoint_id}")
                    methods_failed += 1
                    
            except Exception as e:
                logger.error(f"Error processing {endpoint_id}: {e}")
                methods_failed += 1
        
        result = {
            "methods_processed": methods_processed,
            "methods_failed": methods_failed,
            "output_files": output_files,
            "output_dir": self.output_dir
        }
        
        logger.info(f"DocumentationCreator complete: {methods_processed} processed, {methods_failed} failed")
        return result
