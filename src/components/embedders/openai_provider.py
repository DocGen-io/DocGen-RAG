import os
from typing import Any
from src.utils.logger import DocGenLogger
from src.components.embedders.base_provider import EmbedderProvider
from haystack_integrations.components.embedders.openai import OpenAIDocumentEmbedder
from haystack_integrations.components.embedders.openai import OpenAITextEmbedder
from src.utils.config_loader import get_config_value

logger = DocGenLogger(__name__)


class OpenAIEmbedderProvider(EmbedderProvider):
    """
    Provides OpenAI-based embedders using the openai-haystack integration.
    """
    def __init__(self, config: dict):
        self.model = get_config_value(["rag", "embedding_model"], config)
        openai_config = get_config_value(["generators", "openai"], config) or {}
        self.api_key = openai_config.get("api_key", os.environ.get("OPENAI_API_KEY"))

    def get_document_embedder(self) -> Any:
        logger.info(f"Instantiating OpenAIDocumentEmbedder (model: {self.model})")
        return OpenAIDocumentEmbedder(
            model=self.model,
            api_key=self.api_key,
        )

    def get_text_embedder(self) -> Any:
        logger.info(f"Instantiating OpenAITextEmbedder (model: {self.model})")
        return OpenAITextEmbedder(
            model=self.model,
            api_key=self.api_key,
        )
