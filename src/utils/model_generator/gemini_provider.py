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
        gen_kwargs = extra_kwargs.copy() if extra_kwargs else {}
        
        # Merge default settings for gemini
        gen_kwargs.update({
            "temperature": temperature if temperature is not None else 0,
            "top_p": 0.1,
            "response_mime_type": "application/json",
            "thinking_config": None
        })
        
        if seed is not None:
            gen_kwargs["seed"] = seed

        if format_schema:
            gen_kwargs["response_schema"] = format_schema

        return GoogleGenAIChatGenerator(
            api="vertex",
            vertex_ai_project=settings.get("project_id"),
            vertex_ai_location=settings.get("location"),
            model=settings.get("model"),
            generation_kwargs=gen_kwargs,
            )
