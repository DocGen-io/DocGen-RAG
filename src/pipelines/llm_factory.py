import os
from typing import Optional, Dict, Any
from haystack.components.generators import OpenAIGenerator
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator
from haystack.utils import Secret
from src.core.config import settings

class LLMFactory:
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
            model="llama3",
            url="http://127.0.0.1:11434",
            generation_kwargs={"num_predict": 500}
        )

    @staticmethod
    def _create_google_generator():
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in configuration.")
        return GoogleAIGeminiGenerator(
            model="gemini-pro",
            api_key=Secret.from_token(settings.GOOGLE_API_KEY)
        )

    @staticmethod
    def _create_openai_generator():
        # Assumes OPENAI_API_KEY is set in env or settings
        # config.py doesn't fully expose OPENAI_API_KEY property yet in the snippet I saw, 
        # but the class had it commented or present. 
        # I'll use os.getenv as fallback or assume the user handles it.
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
             raise ValueError("OPENAI_API_KEY is not set.")
        return OpenAIGenerator(
            model="gpt-3.5-turbo",
            api_key=Secret.from_token(api_key)
        )
