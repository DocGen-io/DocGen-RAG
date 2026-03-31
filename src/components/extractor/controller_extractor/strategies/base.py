from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, Tuple
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

class ExtractorStrategy(ABC):
    """Base interface for language-specific controller extraction logic."""
    

        
    def get_base_path(self, captures: Dict[str, Any], get_capture_text_fn: Callable, code_bytes: bytes, class_name: str) -> Optional[str]:
        """Extract the base controller path."""
        raw_base_path = get_capture_text_fn(captures, "class_decorator_path", code_bytes, "").strip("'\"")
        return raw_base_path if raw_base_path else None
        
    def get_endpoint_info(self, captures: Dict[str, Any], get_capture_text_fn: Callable, code_bytes: bytes, class_name: str) -> Tuple[Optional[str], Optional[str], str, str]:
        """Extract method definition, method name, raw decorator type, and raw decorator path for the endpoint."""
        method_def = get_capture_text_fn(captures, "method_definition", code_bytes)
        method_name = get_capture_text_fn(captures, "method_name", code_bytes)
        raw_dec = get_capture_text_fn(captures, "decorator_type", code_bytes, "")
        raw_dec_path = get_capture_text_fn(captures, "decorator_path", code_bytes, "").strip("'\"")
        
        return self._process_endpoint_info(method_def, method_name, raw_dec, raw_dec_path, class_name)
        
    def _process_endpoint_info(self, method_def: Optional[str], method_name: Optional[str], raw_dec: str, raw_dec_path: str, class_name: str) -> Tuple[Optional[str], Optional[str], str, str]:
        """Hook for subclasses to process endpoint info. By default, just returns it."""
        return method_def, method_name, raw_dec, raw_dec_path

class DefaultStrategy(ExtractorStrategy):
    """Default fallback strategy for languages without a specific implementation."""

    def _process_endpoint_info(self, method_def: Optional[str], method_name: Optional[str], raw_dec: str, raw_dec_path: str, class_name: str) -> Tuple[Optional[str], Optional[str], str, str]:
        if not method_name and raw_dec and raw_dec_path:
            clean_path = raw_dec_path.replace("/", "_").replace(":", "").replace("-", "_").replace("{", "").replace("}", "")
            method_name = f"{raw_dec.lower()}_{clean_path}".strip("_")
            method_name = method_name if method_name else f"{raw_dec.lower()}_handler"
        return method_def, method_name, raw_dec, raw_dec_path
