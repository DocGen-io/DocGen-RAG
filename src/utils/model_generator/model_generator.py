from typing import Any, Dict, Optional
from src.utils.config_loader import load_config, get_config_value
from src.utils.logger import DocGenLogger
from .base_provider import BaseProvider
from .ollama_provider import OllamaProvider
from .gemini_provider import GeminiProvider

logger = DocGenLogger(__name__)

# Strategy registry mapping provider names to their factory implementations
PROVIDER_REGISTRY: Dict[str, BaseProvider] = {
    "ollama": OllamaProvider(),
    "gemini": GeminiProvider(),
}

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
        seed: Optional[int] = None,
    ):
        self.llm_type = llm_type
        self.format_schema = format_schema
        self.temperature = temperature
        self.seed = seed
        
        self.config = load_config(config_path)
        if not self.config:
            raise FileNotFoundError(f"Config file not found or empty: {config_path}")

        try:
            self.active_provider = get_config_value([llm_type, "active_generator"], self.config)
            self.provider_settings = get_config_value(["generators", self.active_provider], self.config)

            logger.info(
                f"Active Model: {self.provider_settings.get('model')} via {self.active_provider}",
                location="__init__",
            )
        except KeyError as e:
            raise ValueError(f"Missing configuration key in {config_path}: {e}")

    def get_generator(self, generation_kwargs: Optional[Dict[str, Any]] = None):
        """Create and return the appropriate generator using the OCP strategy registry."""
        
        provider = PROVIDER_REGISTRY.get(self.active_provider)
        
        if not provider:
            raise ValueError(f"Unsupported provider: {self.active_provider}. Add to PROVIDER_REGISTRY.")

        try:
            return provider.create_generator(
                settings=self.provider_settings,
                temperature=self.temperature,
                seed=self.seed,
                format_schema=self.format_schema,
                extra_kwargs=generation_kwargs,
            )
        except Exception as e:
            logger.error(
                f"Failed to initialize {self.active_provider}: {e}",
                location="get_generator",
            )
            raise RuntimeError(
                f"Could not boot the {self.active_provider} generator."
            ) from e