import os
from typing import Any
from src.utils.logger import DocGenLogger
from src.components.embedders.base_provider import EmbedderProvider
from haystack_integrations.components.embedders.google_genai import GoogleGenAIDocumentEmbedder
from haystack_integrations.components.embedders.google_genai import GoogleGenAITextEmbedder
from src.utils.config_loader import get_config_value
logger = DocGenLogger(__name__)

class GeminiEmbedderProvider(EmbedderProvider):
    """
    Provides Google Gemini based embedders using the google-genai-haystack integration.
    """
    def __init__(self, config: dict):

        self.model = get_config_value(["rag","embedding_model"],config)
        gemini_config = get_config_value(['generators','gemini'],config) or {}
        
        # Load from config, fallback to env variables
        self.project_id = gemini_config.get("project_id", os.environ.get("GOOGLE_CLOUD_PROJECT"))
        self.location = gemini_config.get("location", os.environ.get("GOOGLE_CLOUD_LOCATION"))

    def get_document_embedder(self) -> Any:
        logger.info(f"Instantiating GoogleGenAIDocumentEmbedder (model: {self.model})")
        return GoogleGenAIDocumentEmbedder(
          api="vertex", vertex_ai_project=self.project_id, vertex_ai_location=self.location
        )

    def get_text_embedder(self) -> Any:
        logger.info(f"Instantiating GoogleGenAITextEmbedder (model: {self.model})")
        return GoogleGenAITextEmbedder(
            api="vertex", vertex_ai_project=self.project_id, vertex_ai_location=self.location
        )
