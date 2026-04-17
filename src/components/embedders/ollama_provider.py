from typing import Any
from src.utils.logger import DocGenLogger
from src.components.embedders.base_provider import EmbedderProvider
from haystack_integrations.components.embedders.ollama import OllamaDocumentEmbedder
from haystack_integrations.components.embedders.ollama import OllamaTextEmbedder
from src.utils.config_loader import get_config_value
logger = DocGenLogger(__name__)

class OllamaEmbedderProvider(EmbedderProvider):
    """
    Provides local Ollama based embedders using the ollama-haystack integration.
    """
    def __init__(self, config: dict):
        self.model = get_config_value(["rag","embedding_model"],config)
        self.url = get_config_value(["generators","ollama","url"],config)

    def get_document_embedder(self) -> Any:
        logger.info(f"Instantiating OllamaDocumentEmbedder (model: {self.model})")
        return OllamaDocumentEmbedder(model=self.model, url=self.url)

    def get_text_embedder(self) -> Any:
        logger.info(f"Instantiating OllamaTextEmbedder (model: {self.model})")
        return OllamaTextEmbedder(model=self.model, url=self.url)
