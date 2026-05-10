import os
from typing import Any, Dict, Optional
from haystack_integrations.components.generators.openai import OpenAIChatGenerator
from .base_provider import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI LLM provider strategy for the model generator."""

    def create_generator(
        self,
        settings: Dict[str, Any],
        temperature: Optional[float],
        seed: Optional[int],
        format_schema: Optional[Dict],
        extra_kwargs: Optional[Dict[str, Any]] = None,
    ) -> OpenAIChatGenerator:
        gen_kwargs = self._get_common_params(settings, temperature, seed, extra_kwargs)

        # Map standardized names to OpenAI-specific names
        max_tokens = gen_kwargs.pop("max_tokens")
        gen_kwargs["max_tokens"] = max_tokens  # OpenAI uses max_tokens directly

        # JSON mode
        if format_schema:
            gen_kwargs["response_format"] = {"type": "json_object"}

        api_key = settings.get("api_key", os.environ.get("OPENAI_API_KEY"))

        return OpenAIChatGenerator(
            model=settings.get("model", "gpt-4o"),
            api_key=api_key,
            generation_kwargs=gen_kwargs,
        )
