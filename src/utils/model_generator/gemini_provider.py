from typing import Any, Dict, Optional
from haystack_integrations.components.generators.google_genai import (
    GoogleGenAIChatGenerator,
)
from .base_provider import BaseProvider

class GeminiProvider(BaseProvider):
    def create_generator(
        self,
        settings: Dict[str, Any],
        temperature: Optional[float],
        seed: Optional[int],
        format_schema: Optional[Dict],
        extra_kwargs: Optional[Dict[str, Any]] = None
    ) -> GoogleGenAIChatGenerator:
        gen_kwargs = self._get_common_params(settings, temperature, seed, extra_kwargs)
        
        # Map standardized names to Gemini-specific API names
        max_tokens = gen_kwargs.pop("max_tokens")
        gen_kwargs.update({
            "max_output_tokens": max_tokens,
            "top_p": 0.1,
            "thinking_config": None
        })
        
        # Standardized JSON/Text logic
        if format_schema:
            gen_kwargs["response_mime_type"] = "application/json"
            gen_kwargs["response_schema"] = format_schema
        elif "response_mime_type" not in gen_kwargs:
            gen_kwargs["response_mime_type"] = "text/plain"

        import os
        return GoogleGenAIChatGenerator(
            api="vertex",
            vertex_ai_project=settings.get("project_id") or os.environ.get("GOOGLE_CLOUD_PROJECT"),
            vertex_ai_location=settings.get("location") or os.environ.get("GOOGLE_CLOUD_LOCATION"),
            model=settings.get("model"),
            generation_kwargs=gen_kwargs,
        )
