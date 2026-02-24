"""
ModelGenerator — Abstract LLM factory with constrained decoding support.

Creates the appropriate Haystack generator based on config.yaml,
supporting format_schema (JSON schema for constrained decoding)
and temperature parameters via generation_kwargs.
"""

from typing import Any, Dict, Optional
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack_integrations.components.generators.google_genai import (
    GoogleGenAIChatGenerator,
)
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


class ModelGenerator:
    """
    Factory for creating LLM generators from config.yaml.

    Args:
        llm_type: Config section key (e.g. 'code_mapper', 'doc_creator')
        config_path: Path to config.yaml
        format_schema: Optional JSON schema dict for constrained decoding
        temperature: Optional temperature for generation
    """

    def __init__(
        self,
        llm_type: str,
        config_path: str = "config.yaml",
        format_schema: Optional[dict] = None,
        temperature: Optional[float] = None,
    ):
        self.llm_type = llm_type
        self.format_schema = format_schema
        self.temperature = temperature
        self.config = load_config(config_path)
        if not self.config:
            raise FileNotFoundError(f"Config file not found or empty: {config_path}")

        try:
            self.phase_config = self.config[llm_type]
            self.active_provider = self.phase_config["active_generator"]
            self.provider_settings = self.config["generators"][self.active_provider]
            logger.info(
                f"Active Model: {self.provider_settings.get('model')}",
                location="__init__",
            )
        except KeyError as e:
            raise ValueError(f"Missing configuration key in {config_path}: {e}")

    def get_generator(self,  generation_kwargs: dict[str, Any] | None = None,):
        """Create and return the appropriate generator (lazy loading)."""
        model = self.provider_settings.get("model")
        url = self.provider_settings.get("url")

        try:
            if self.active_provider == "ollama":
                return self._create_ollama(model, url,  generation_kwargs)
            elif self.active_provider == "gemini":
                return self._create_gemini(model)
            else:
                raise ValueError(f"Unsupported provider: {self.active_provider}")
        except ValueError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to initialize {self.active_provider}: {e}",
                location="get_generator",
            )
            raise RuntimeError(
                f"Could not boot the {self.active_provider} generator."
            ) from e

    def _create_ollama(self, model: str, url: str, generation_kwargs: dict[str, Any] | None = None) -> OllamaGenerator:
        """Create OllamaGenerator with schema in generation_kwargs."""
        gen_kwargs = {}

        # Schema for constrained decoding, or plain "json" as fallback
        gen_kwargs["format"] = self.format_schema if self.format_schema else "json"

        if self.temperature is not None:
            gen_kwargs["temperature"] = self.temperature

        return OllamaGenerator(
            model=model,
            url=url,
            generation_kwargs=gen_kwargs,
        )

    def _create_gemini(self, model: str) -> GoogleGenAIChatGenerator:
        """Create Google Gemini chat generator."""
        return GoogleGenAIChatGenerator(model=model)