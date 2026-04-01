from typing import Any, Dict, Optional
from haystack_integrations.components.generators.ollama import OllamaChatGenerator
from .base_provider import BaseProvider

class OllamaProvider(BaseProvider):
    def create_generator(
        self,
        settings: Dict[str, Any],
        temperature: Optional[float],
        seed: Optional[int],
        format_schema: Optional[Dict],
        extra_kwargs: Optional[Dict[str, Any]] = None
    ) -> OllamaChatGenerator:
        gen_kwargs = extra_kwargs.copy() if extra_kwargs else {}
        
        # Schema for constrained decoding, or plain "json" as fallback
        gen_kwargs["format"] = format_schema if format_schema else "json"
        
        # Default to temperature=0 for deterministic output
        gen_kwargs["temperature"] = temperature if temperature is not None else 0
        
        if seed is not None:
            gen_kwargs["seed"] = seed

        return OllamaChatGenerator(
            model=settings.get("model"),
            url=settings.get("url"),
            generation_kwargs=gen_kwargs,
        )
