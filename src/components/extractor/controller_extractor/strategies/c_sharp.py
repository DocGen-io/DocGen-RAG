import re
from typing import Optional, Dict, Any, Callable, Tuple
from .base import ExtractorStrategy

class CSharpStrategy(ExtractorStrategy):
    """C# specific extraction logic for ASP.NET Controllers."""
    
    def _resolve_routing_tokens(self, path: str, class_name: str, method_name: Optional[str] = None) -> str:
        if not path:
            return path
        
        if "[controller]" in path.lower():
            route_class_name = class_name[:-10] if class_name.endswith("Controller") else class_name
            path = re.sub(r'\[controller\]', route_class_name, path, flags=re.IGNORECASE)
        if method_name and "[action]" in path.lower():
            route_method_name = method_name[:-5] if method_name.endswith("Async") else method_name
            path = re.sub(r'\[action\]', route_method_name, path, flags=re.IGNORECASE)
        return path

    def get_base_path(self, captures: Dict[str, Any], get_capture_text_fn: Callable, code_bytes: bytes, class_name: str) -> Optional[str]:
        raw_base_path = super().get_base_path(captures, get_capture_text_fn, code_bytes, class_name)
        return self._resolve_routing_tokens(raw_base_path, class_name) if raw_base_path else None
        
    def _process_endpoint_info(self, method_def: Optional[str], method_name: Optional[str], raw_dec: str, raw_dec_path: str, class_name: str) -> Tuple[Optional[str], Optional[str], str, str]:
        dec_path = self._resolve_routing_tokens(raw_dec_path, class_name, method_name)
        return method_def, method_name, raw_dec, dec_path
