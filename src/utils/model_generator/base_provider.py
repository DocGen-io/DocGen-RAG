from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

class BaseProvider(ABC):
    """Abstract base class for LLM generator providers."""
    
    @abstractmethod
    def create_generator(
        self,
        settings: Dict[str, Any],
        temperature: Optional[float],
        seed: Optional[int],
        format_schema: Optional[Dict],
        extra_kwargs: Optional[Dict[str, Any]] = None
    ) -> Any:
        pass
