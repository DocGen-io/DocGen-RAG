"""
Swagger/OpenAPI 3.0 builder for creating valid OpenAPI specifications.

OpenAPI Specification Reference: https://swagger.io/specification/
OpenAPI 3.0.3 Schema: https://spec.openapis.org/oas/v3.0.3
"""
from typing import Dict, Any, List, Optional
import re, logging
from src.utils.output_format_builders.base import OutputFormatBuilder

logger = logging.getLogger(__name__)


class SwaggerBuilder(OutputFormatBuilder):
    """
    Builder for OpenAPI 3.0 specifications.
    
    Converts individual endpoint swagger.json files into a complete OpenAPI spec.
    Handles common LLM output issues like Swagger 2.0 format, $ref without components, etc.
    """
    
    OPENAPI_VERSION = "3.0.3"
    # GET/HEAD/DELETE should not have requestBody per OpenAPI spec
    NO_BODY_METHODS = {"get", "head", "delete"}
    
    def __init__(self, title: str = "API Documentation", version: str = "1.0.0",
                 description: str = "", base_url: Optional[str] = None):
        self.title, self.version, self.description, self.base_url = title, version, description, base_url
    
    def build(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Build complete OpenAPI 3.0 spec from individual endpoint data.
        
        Each endpoint dict should have: method_name, http_method, data (swagger content)
        See: https://swagger.io/specification/#paths-object
        """
        spec = {
            "openapi": self.OPENAPI_VERSION,
            "info": {"title": self.title, "version": self.version, "description": self.description},
            "paths": {}
        }
        if self.base_url:
            spec["servers"] = [{"url": self.base_url}]
        
        for ep in endpoints:
            http_method = ep.get("http_method", "GET").lower()
            data = ep.get("data", {})
            path = self._normalize_path(data.get("path") or f"/{ep.get('method_name', 'unknown')}")
            
            if path not in spec["paths"]:
                spec["paths"][path] = {}
            spec["paths"][path][http_method] = self._build_operation(data, http_method, path)
        
        return spec
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize path: ensure leading slash, convert Express :param to OpenAPI {param}.
        Example: /users/:id -> /users/{id}
        """
        if not path:
            return "/"
        path = path if path.startswith("/") else f"/{path}"
        # Convert Express-style :param to OpenAPI {param}
        return re.sub(r':([a-zA-Z_][a-zA-Z0-9_]*)', r'{\1}', path)
    
    def _build_operation(self, data: Dict[str, Any], http_method: str, path: str) -> Dict[str, Any]:
        """
        Build an Operation Object for a single endpoint.
        See: https://swagger.io/specification/#operation-object
        """
        # Extract path params from path template (e.g., {id} from /users/{id})
        path_params = set(re.findall(r'\{([^}]+)\}', path))
        op = {}
        
        # Copy basic operation fields
        for key in ["summary", "description", "security"]:
            if key in data:
                op[key] = data[key]
        
        if "parameters" in data:
            op["parameters"] = self._normalize_parameters(data["parameters"], path_params)
        
        # Only add requestBody for POST/PUT/PATCH (not GET/HEAD/DELETE)
        if http_method not in self.NO_BODY_METHODS and "requestBody" in data:
            op["requestBody"] = self._normalize_request_body(data["requestBody"])
        
        op["responses"] = self._normalize_responses(data.get("responses"))
        return op
    
    def _normalize_parameters(self, params: List[Dict], path_params: set) -> List[Dict]:
        """
        Normalize parameters to OpenAPI 3.0 format.
        
        - Converts Swagger 2.0 'type' to 'schema' object
        - Ensures 'required' field exists (path params are always required)
        - Skips 'body' params (handled by requestBody in OpenAPI 3.0)
        - Validates path params exist in URL template
        
        See: https://swagger.io/specification/#parameter-object
        """
        result = []
        for p in params:
            # In OpenAPI 3.0, body params are handled via requestBody
            if p.get("in") == "body":
                continue
            
            name, loc = p.get("name", "unnamed"), p.get("in", "query")
            
            # Path params must exist in the URL template
            if loc == "path" and name not in path_params:
                logger.warning(f"Skipping path parameter '{name}' - not in path template")
                continue
            
            # Build schema object (OpenAPI 3.0 requires schema, not type at param level)
            schema = p.get("schema") or {"type": p.get("type", "string")}
            for prop in ["default", "minimum", "maximum", "enum", "format"]:
                if prop in p and prop not in schema:
                    schema[prop] = p[prop]
            
            # Path params must be required=true
            norm = {"name": name, "in": loc, "required": True if loc == "path" else p.get("required", False), "schema": schema}
            if "description" in p:
                norm["description"] = p["description"]
            result.append(norm)
        return result
    
    def _normalize_request_body(self, rb: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize requestBody to OpenAPI 3.0 format.
        See: https://swagger.io/specification/#request-body-object
        """
        if not rb:
            return {"content": {"application/json": {"schema": {"type": "object"}}}}
        
        result = {}
        if "description" in rb:
            result["description"] = rb["description"]
        if "required" in rb:
            result["required"] = rb["required"]
        
        if "content" in rb:
            result["content"] = {}
            for mt, obj in rb["content"].items():
                if isinstance(obj, dict):
                    # Handle common typo: 'schemas' instead of 'schema'
                    schema = obj.get("schema") or obj.get("schemas") or {"type": "object"}
                    result["content"][mt] = {"schema": self._normalize_schema(schema)}
        else:
            result["content"] = {"application/json": {"schema": {"type": "object"}}}
        
        return result
    
    def _normalize_schema(self, schema: Any) -> Dict[str, Any]:
        """
        Normalize schema objects and inline $ref references.
        
        Since we don't generate components/schemas, we inline all $ref as generic objects.
        Also handles named schemas like {"UserDto": {type: object}} -> extracts inner schema.
        
        See: https://swagger.io/specification/#schema-object
        """
        if not isinstance(schema, dict):
            return {"type": "object"}
        
        # Extract named schemas like {"UserDto": {properties: ...}}
        if len(schema) == 1:
            key = next(iter(schema))
            if key not in ["type", "$ref", "properties", "items", "allOf", "oneOf", "anyOf"]:
                return self._normalize_schema(schema[key])
        
        # Inline $ref since we don't have components defined
        if "$ref" in schema:
            type_name = schema["$ref"].split("/")[-1].replace("[]", "")
            if "[]" in schema["$ref"]:
                return {"type": "array", "items": {"type": "object", "description": f"Item of {type_name}"}}
            return {"type": "object", "description": f"Object of type {type_name}"}
        
        # Recursively process nested schemas
        result = {}
        for k, v in schema.items():
            if k in ("items", "properties") and isinstance(v, dict):
                result[k] = {sk: self._normalize_schema(sv) if isinstance(sv, dict) else sv for sk, sv in v.items()} if k == "properties" else self._normalize_schema(v)
            else:
                result[k] = v
        return result
    
    def _normalize_responses(self, responses: Any) -> Dict[str, Any]:
        """
        Normalize responses to OpenAPI 3.0 format.
        
        Handles:
        - Array format: [{"code": 200, "description": "OK"}] -> {"200": {"description": "OK"}}
        - Dict format: {200: {...}} -> {"200": {...}}
        
        See: https://swagger.io/specification/#responses-object
        """
        if not responses:
            return {"200": {"description": "Success"}}
        
        if isinstance(responses, dict):
            return {str(k): self._normalize_response(v) if isinstance(v, dict) else {"description": "Response"} for k, v in responses.items()}
        
        if isinstance(responses, list):
            result = {}
            for r in responses:
                if isinstance(r, dict):
                    result[str(r.get("code", r.get("status", 200)))] = self._normalize_response(r)
            return result or {"200": {"description": "Success"}}
        
        return {"200": {"description": "Success"}}
    
    def _normalize_response(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single Response Object. See: https://swagger.io/specification/#response-object"""
        res = {"description": r.get("description", "Response")}
        if "content" in r:
            res["content"] = {mt: {"schema": self._normalize_schema(obj.get("schema", {}))} for mt, obj in r["content"].items() if isinstance(obj, dict)}
        elif "schema" in r:
            res["content"] = {"application/json": {"schema": self._normalize_schema(r["schema"])}}
        return res
    
    def validate(self, output: Dict[str, Any]) -> bool:
        """Validate that output has required OpenAPI 3.0 fields."""
        return all(f in output for f in ["openapi", "info", "paths"]) and \
               "title" in output.get("info", {}) and "version" in output.get("info", {})
