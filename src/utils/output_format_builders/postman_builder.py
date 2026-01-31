"""Postman Collection v2.1 builder."""
from typing import Dict, Any, List, Optional
from src.utils.output_format_builders.base import OutputFormatBuilder


class PostmanCollectionBuilder(OutputFormatBuilder):
    """Builder for Postman Collection v2.1 format."""
    
    POSTMAN_SCHEMA = "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    
    def __init__(self, collection_name: str = "API Collection", base_url: Optional[str] = None):
        self.collection_name, self.base_url = collection_name, base_url
    
    def build(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "info": {"name": self.collection_name, "schema": self.POSTMAN_SCHEMA},
            "item": [self._build_item(ep.get("method_name", "unknown"), ep.get("data", {})) for ep in endpoints]
        }
    
    def _build_item(self, method_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        return {"name": data.get("name", method_name), "request": self._build_request(data)}
    
    def _build_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        if not data.get("method") or not data.get("url"):
            return {}
        req = {
            "method": data.get("method", "GET"),
            "header": self._normalize_headers(data.get("header", data.get("headers", []))),
            "url": self._build_url(data.get("url", "/"))
        }
        if data.get("body"):
            req["body"] = data["body"]
        if data.get("description"):
            req["description"] = data["description"]
        return req
    
    def _normalize_headers(self, headers: Any) -> List[Dict[str, str]]:
        if not headers:
            return []
        if isinstance(headers, dict):
            return [{"key": k, "value": v} for k, v in headers.items()]
        if isinstance(headers, list):
            return [{"key": h.get("key") or h.get("name", ""), "value": h.get("value", "")} 
                    for h in headers if isinstance(h, dict) and (h.get("key") or h.get("name"))]
        return []
    
    def _build_url(self, url: str) -> Dict[str, Any]:
        url = url or "/"
        if self.base_url:
            raw = f"{self.base_url.rstrip('/')}/{url.lstrip('/')}"
            host = [self.base_url.replace("http://", "").replace("https://", "")]
        else:
            raw = f"{{{{baseUrl}}}}{url if url.startswith('/') else '/' + url}"
            host = ["{{baseUrl}}"]
        
        path_part = url.split("?")[0].strip("/")
        result = {"raw": raw, "host": host, "path": path_part.split("/") if path_part else []}
        
        if "?" in url:
            result["query"] = [{"key": k, "value": v} for p in url.split("?")[1].split("&") 
                              for k, v in [p.split("=", 1)] if "=" in p]
        return result
    
    def validate(self, output: Dict[str, Any]) -> bool:
        return "info" in output and "name" in output.get("info", {}) and \
               "schema" in output.get("info", {}) and "item" in output
