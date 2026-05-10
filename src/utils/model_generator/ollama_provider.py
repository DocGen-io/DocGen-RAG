import os
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
        gen_kwargs = self._get_common_params(settings, temperature, seed, extra_kwargs)
        
        # Map standardized names to Ollama-specific names
        max_tokens = gen_kwargs.pop("max_tokens")
        gen_kwargs["num_predict"] = max_tokens
        
        # Standardized JSON/Text logic (matching Gemini behavior)
        if format_schema:
            gen_kwargs["format"] = format_schema
        else:
            gen_kwargs["format"] = ""

        return OllamaChatGenerator(
            model=settings.get("model"),
            url=settings.get("url") or os.environ.get("OLLAMA_URL") or "http://127.0.0.1:11434",
            generation_kwargs=gen_kwargs,
        )
