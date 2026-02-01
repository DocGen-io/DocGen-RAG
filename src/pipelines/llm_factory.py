import os
from typing import Optional
from haystack.components.generators import OpenAIGenerator
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator
from haystack.utils import Secret
from src.utils.config_loader import load_config


class LLMFactory:
    """Factory for creating LLM generators based on config."""
    
    _config = None
    
    @classmethod
    def _get_config(cls):
        if cls._config is None:
            cls._config = load_config()
        return cls._config
    
    @staticmethod
    def get_generator(llm_type: str = "local"):
        """
        Factory method to return the appropriate generator based on the type.
        """
        llm_type = llm_type.lower()
        
        if llm_type == "local":
            return LLMFactory._create_local_generator()
        elif llm_type == "google":
            return LLMFactory._create_google_generator()
        elif llm_type == "openai":
            return LLMFactory._create_openai_generator()
        else:
            raise ValueError(f"Unsupported LLM type: {llm_type}")

    @staticmethod
    def _create_local_generator():
        # Assumes Ollama is running locally
        return OllamaGenerator(
            model="devstral-small-2:24b",
            url="http://0.0.0.0:11434",
            generation_kwargs={"num_predict": 500}
        )

    @staticmethod
    def _create_google_generator():
        config = LLMFactory._get_config()
        api_key = config.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not set in config.yaml or environment.")
        return GoogleAIGeminiGenerator(
            model="gemini-pro",
            api_key=Secret.from_token(api_key)
        )

    @staticmethod
    def _create_openai_generator():
        config = LLMFactory._get_config()
        api_key = config.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in config.yaml or environment.")
        return OpenAIGenerator(
            model="gpt-3.5-turbo",
            api_key=Secret.from_token(api_key)
        )
