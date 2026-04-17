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

    def _get_common_params(
        self,
        settings: Dict[str, Any],
        temperature: Optional[float],
        seed: Optional[int],
        extra_kwargs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Compute standard parameters shared across all providers."""
        params = extra_kwargs.copy() if extra_kwargs else {}
        
        # 1. Deterministic defaults
        params["temperature"] = temperature if temperature is not None else 0
        if seed is not None:
            params["seed"] = seed
            
        # 2. Token limits (from settings or 8192 default)
        params["max_tokens"] = settings.get("max_tokens", 8192)
        
        return params
