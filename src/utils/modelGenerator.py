import logging
from typing import Any, Dict
from haystack_integrations.components.generators.ollama import OllamaGenerator
from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator
from src.utils.config_loader import load_config

logger = logging.getLogger(__name__)

class ModelGenerator:
    def __init__(self, llm_type: str, config_path: str = "config.yaml"):
        self.llm_type = llm_type
        self.config = load_config(config_path)
        if not self.config:
            raise FileNotFoundError(f"Config file not found or empty: {config_path}")
        
        try:
            self.phase_config = self.config[llm_type]
            self.active_provider = self.phase_config["active_generator"]
            self.provider_settings = self.phase_config['generators'][self.active_provider]
            print(f"Active Model: {self.provider_settings.get('model')}")
        except KeyError as e:
            raise ValueError(f"Missing configuration key in {config_path}: {e}")

    def get_generator(self):
        """
        Initializes the generator only when requested (Lazy Loading).
        """
        model = self.provider_settings.get("model")
        url = self.provider_settings.get("url")

        try:
            if self.active_provider == "ollama":
                return OllamaGenerator(model=model, url=url)
            
            elif self.active_provider == "googlegemini":
                # Ensure you have GOOGLE_API_KEY in your environment
                return GoogleAIGeminiGenerator(model=model)
            
            else:
                raise ValueError(f"Unsupported provider: {self.active_provider}")
        
        except Exception as e:
            logger.error(f"Failed to initialize {self.active_provider}: {e}")
            raise RuntimeError(f"Could not boot the {self.active_provider} generator.") from e