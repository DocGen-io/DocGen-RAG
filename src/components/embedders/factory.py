from typing import Dict, Type
from src.components.embedders.base_provider import EmbedderProvider
from src.components.embedders.gemini_provider import GeminiEmbedderProvider
from src.components.embedders.ollama_provider import OllamaEmbedderProvider
from src.utils.config_loader import get_config_value


class EmbedderFactory:
    _providers: Dict[str, Type[EmbedderProvider]] = {
        "gemini": GeminiEmbedderProvider,
        "ollama": OllamaEmbedderProvider,
    }

    @classmethod
    def register_provider(cls, name: str, provider_class: Type[EmbedderProvider]):
        """Register a new embedder provider."""
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, config: dict) -> EmbedderProvider:
        """
        Instantiate the active embedder provider based on configuration.
        """
        provider_name = get_config_value(["rag","active_embedder"],config).lower()
        provider_class = cls._providers.get(provider_name)
        
        if not provider_class:
            keys = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown embedder provider: '{provider_name}'. Available options: {keys}")
        
        return provider_class(config)


# Register OpenAI only if its haystack integration is installed
try:
    from src.components.embedders.openai_provider import OpenAIEmbedderProvider
    EmbedderFactory.register_provider("openai", OpenAIEmbedderProvider)
except ImportError:
    pass
