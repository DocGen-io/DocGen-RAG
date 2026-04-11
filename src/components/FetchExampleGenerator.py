"""
FetchExampleGenerator - Generates framework-specific fetch code examples for API endpoints.

Standalone component (on-demand, not part of the main pipeline).
Takes swagger documentation for an endpoint and generates code examples
in JavaScript (fetch), Python (requests), and cURL.
"""

import json
import argparse
from typing import Dict, Any, Optional
from haystack.dataclasses import ChatMessage

from haystack import component
from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
from src.utils.model_generator import ModelGenerator
from src.utils.llm_json_handler import LLMJsonHandler
from prompts import fetch_example_system_prompt, fetch_example_user_prompt

logger = DocGenLogger(__name__)


@component
class FetchExampleGenerator:
    """
    Generates fetch code examples for an API endpoint.
    Not part of the main pipeline — called on demand.
    """

    def __init__(self, config_path: str = "config.yaml", weaviate_url: Optional[str] = None):
        config = load_config(config_path)
        self.weaviate_url = weaviate_url or config.get("weaviate", {}).get("url", "http://localhost:8080")
        
        gen_section = config.get("fetch_example_generator", {}).get(
            "active_generator", config.get("doc_creator", {}).get("active_generator", "ollama")
        )
        # Reuse doc_creator config if no dedicated section exists
        llm_type = "fetch_example_generator" if "fetch_example_generator" in config else "doc_creator"
        self.generator = ModelGenerator(llm_type, config_path).get_generator()

    def _build_prompt(self, swagger: Dict[str, Any]):
        """Build system + user messages from swagger data."""
        params = swagger.get("parameters", [])
        params_str = json.dumps(params, indent=2) if params else "None"

        request_body = swagger.get("requestBody", {})
        body_str = json.dumps(request_body, indent=2) if request_body else "None"

        user_prompt = fetch_example_user_prompt.substitute(
            http_method=swagger.get("method", "GET").upper(),
            endpoint_path=swagger.get("path", "/"),
            summary=swagger.get("summary", ""),
            parameters=params_str,
            request_body=body_str,
        )
        return [
            ChatMessage.from_system(fetch_example_system_prompt),
            ChatMessage.from_user(user_prompt)
        ]

    @component.output_types(examples=Dict[str, str])
    def run(self, 
            team_id: str, 
            project_name: str, 
            path: str, 
            method: str,
            swagger_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Generate fetch code examples for an endpoint by fetching data from Weaviate.
        If swagger_data is provided, it skips the Weaviate fetch (backward compatibility/testing).
        """
        if not swagger_data:
            from src.serviceLayer.endpoint_service import EndpointService
            service = EndpointService(self.weaviate_url)
            swagger_data = service.fetch_endpoint(project_name, team_id, path, method)
            
        if not swagger_data:
            logger.error(f"Could not find swagger data for {method.upper()} {path} in Weaviate")
            return {"examples": {}}

        prompt = self._build_prompt(swagger_data)
        try:
            result = self.generator.run(messages=prompt)
            if 'replies' in result and result['replies']:
                text = result['replies'][0].text
                parsed = LLMJsonHandler.safe_parse(text, fallback={})
                
                # Aggressively find all framework/code pairs
                flattened = {}
                
                def find_pairs(obj):
                    if isinstance(obj, dict):
                        fw = obj.get("framework") or obj.get("name")
                        cd = obj.get("code") or obj.get("snippet")
                        if fw and cd and isinstance(cd, str):
                            flattened[str(fw)] = cd
                        for v in obj.values():
                            find_pairs(v)
                    elif isinstance(obj, list):
                        for item in obj:
                            find_pairs(item)

                find_pairs(parsed)
                
                # Fallback: if empty, maybe it's already a flat dict {lang: code}
                if not flattened and isinstance(parsed, dict):
                    for k, v in parsed.items():
                        if isinstance(v, str) and k != "status":
                            flattened[str(k)] = v

                return {"examples": flattened}
                    
            return {"examples": {}}
        except Exception as e:
            logger.error(f"Failed to generate fetch examples: {e}")
            return {"examples": {}}

def main():
    parser = argparse.ArgumentParser(description="Generate fetch code examples for an API endpoint.")
    parser.add_argument("--swagger_path", type=str, required=True, help="Path to the swagger file.")
    parser.add_argument("--config_path", type=str, default="config.yaml", help="Path to the config file.")
    args = parser.parse_args()
    
    generator = FetchExampleGenerator(config_path=args.config_path)
    swagger_data = json.load(open(args.swagger_path))
    
    examples = generator.run(swagger_data)
    
    logger.info(examples)