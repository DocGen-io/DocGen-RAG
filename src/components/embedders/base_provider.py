from abc import ABC, abstractmethod
from typing import Any

class EmbedderProvider(ABC):
    """
    Base interface for embedding providers.
    Following the Strategy pattern to allow seamless swapping of embedders.
    """
    
    @abstractmethod
    def get_document_embedder(self) -> Any:
        """Returns a Haystack DocumentEmbedder instance."""
        pass

    @abstractmethod
    def get_text_embedder(self) -> Any:
        """Returns a Haystack TextEmbedder instance."""
        pass
