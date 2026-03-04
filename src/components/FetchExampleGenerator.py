"""
FetchExampleGenerator - Generates framework-specific fetch code examples for API endpoints.

Standalone component (on-demand, not part of the main pipeline).
Takes swagger documentation for an endpoint and generates code examples
in JavaScript (fetch), Python (requests), and cURL.
"""

import json
from typing import Dict, Any, Optional

from haystack import component

from src.utils.logger import DocGenLogger
from src.utils.config_loader import load_config
from src.utils.modelGenerator import ModelGenerator
from src.utils.llm_json_handler import LLMJsonHandler
from prompts.fetchExamplePrompt import fetch_example_prompt

logger = DocGenLogger(__name__)


@component
class FetchExampleGenerator:
    """
    Generates fetch code examples for an API endpoint.
    Not part of the main pipeline — called on demand.
    """

    def __init__(self, config_path: str = "config.yaml"):
        config = load_config(config_path)
        gen_section = config.get("fetch_example_generator", {}).get(
            "active_generator", config.get("doc_creator", {}).get("active_generator", "ollama")
        )
        # Reuse doc_creator config if no dedicated section exists
        llm_type = "fetch_example_generator" if "fetch_example_generator" in config else "doc_creator"
        self.generator = ModelGenerator(llm_type, config_path).get_generator()

    def _build_prompt(self, swagger: Dict[str, Any]):
        """Build prompt from swagger data."""
        params = swagger.get("parameters", [])
        params_str = json.dumps(params, indent=2) if params else "None"

        request_body = swagger.get("requestBody", {})
        body_str = json.dumps(request_body, indent=2) if request_body else "None"

        prompt_str = fetch_example_prompt.substitute(
            http_method=swagger.get("method", "GET").upper(),
            endpoint_path=swagger.get("path", "/"),
            summary=swagger.get("summary", ""),
            parameters=params_str,
            request_body=body_str,
        )
        from haystack.dataclasses import ChatMessage
        return ChatMessage.from_user(prompt_str)

    @component.output_types(examples=Dict[str, str])
    def run(self, swagger_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate fetch code examples for an endpoint.

        Args:
            swagger_data: Swagger/OpenAPI data for a single endpoint.

        Returns:
            Dictionary with 'examples' mapping framework -> code string.
        """
        if not swagger_data or not swagger_data.get("path"):
            return {"examples": {}}

        prompt = self._build_prompt(swagger_data)

        try:
            result = LLMJsonHandler.parse_with_retry(
                generator=self.generator, prompt=prompt, max_retries=2
            )
            return {"examples": result}
        except Exception as e:
            logger.error(f"Failed to generate fetch examples: {e}")
            return {"examples": {}}
