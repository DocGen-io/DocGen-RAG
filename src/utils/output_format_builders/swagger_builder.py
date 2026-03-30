"""
Swagger/OpenAPI 3.0 builder for creating valid OpenAPI specifications.

OpenAPI Specification Reference: https://swagger.io/specification/
OpenAPI 3.0.3 Schema: https://spec.openapis.org/oas/v3.0.3
"""
from typing import Dict, Any, List, Optional
import re, logging
from src.utils.output_format_builders.base import OutputFormatBuilder
from src.utils.definitions import API_METHODS
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)


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
            
        valid_methods = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
        
        for ep in endpoints:
            http_method = ep.get("http_method", "GET").lower()
            if http_method not in valid_methods:
                logger.warning(f"Skipping endpoint {ep.get('method_name')} with invalid HTTP method: {http_method}")
                continue
                
            data = ep.get("data", {})
            original_path = data.get("path") or f"/{ep.get('method_name', 'unknown')}"
            path = self._normalize_path(original_path)
            
            # Deduplicator: If this path+method combination already exists, we skip it
            # instead of creating a fake/modified path, ensuring the true API path is strictly presented.
            if path in spec["paths"] and http_method in spec["paths"][path]:
                logger.warning(
                    f"Duplicate API route detected: {http_method.upper()} {path} "
                    f"(from {ep.get('method_name')}). Skipping to preserve the original, canonical path."
                )
                continue
            
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
        elif path_params:
            # If LLM completely forgot the parameters array but the path has {var}, we must inject them
            op["parameters"] = self._normalize_parameters([], path_params)
        
        # Only add requestBody for POST/PUT/PATCH (not GET/HEAD/DELETE)
        if http_method not in self.NO_BODY_METHODS and "requestBody" in data:
            op["requestBody"] = self._normalize_request_body(data["requestBody"])
        
        # OpenAPI 3.0 STRICT RULE: Every operation MUST have at least one response
        op["responses"] = self._normalize_responses(data.get("responses"))
        if not op["responses"]:
            logger.warning(f"Operation {http_method.upper()} {path} missing responses. Auto-injecting default 200.")
            op["responses"] = {"200": {"description": "Successful operation"}}
            
        return op
    
    def _normalize_parameters(self, params: List[Dict], path_params: set) -> List[Dict]:
        """
        Normalize parameters to OpenAPI 3.0 format.
        
        - Converts Swagger 2.0 'type' to 'schema' object
        - Ensures 'required' field exists (path params are always required)
        - Skips 'body' and 'formData' params (handled by requestBody in OpenAPI 3.0)
        - Strictly validates 'in' is one of: query, header, path, cookie
        - Fixes LLM path location mismatches automatically.
        
        See: https://swagger.io/specification/#parameter-object
        """
        result = []
        valid_locations = {"query", "header", "path", "cookie"}
        seen_path_params = set()
        
        for p in params:
            loc = p.get("in", "query").lower()
            name = p.get("name", "unnamed")
            
            # Auto-correction: If the parameter name is explicitly in the URL path template,
            # it MUST be "in": "path" according to OpenAPI, regardless of what the LLM generated.
            if name in path_params:
                loc = "path"

            # In OpenAPI 3.0, body and formData params are handled via requestBody,
            # and any other random hallucinated location is strictly invalid.
            if loc not in valid_locations:
                if loc not in {"body", "formdata"}:
                    logger.warning(f"Skipping parameter '{name}' with invalid OpenAPI 3.0 location: {loc}")
                continue
            
            if loc == "path":
                # Path params MUST exist in the URL template
                if name not in path_params:
                    logger.warning(f"Skipping path parameter '{name}' - not in path template")
                    continue
                seen_path_params.add(name)
            
            # Build schema object (OpenAPI 3.0 requires schema, not type at param level)
            schema = p.get("schema") or {"type": p.get("type", "string")}
            schema = self._normalize_schema(schema)
            
            # OpenAPI 3.0 limits complex objects inside 'query' unless `style`/`explode` are configured.
            if loc == "query" and schema.get("type") == "object":
                if "properties" not in schema:
                    # Opaque DTO ref (no properties, just a description like "Object of type PaginationQueryDto").
                    # Drop it entirely — it carries no useful information and confuses Swagger UI.
                    logger.warning(f"Dropping opaque object query parameter '{name}' (no properties). Likely an unexpanded DTO.")
                    continue
                # Has real properties — flatten to string to prevent Swagger UI from crashing.
                logger.warning(f"Flattening complex object query parameter '{name}' to string. (Did LLM mean requestBody?)")
                schema = {"type": "string", "description": "Serialized object data"}

            for prop in ["default", "minimum", "maximum", "enum", "format"]:
                if prop in p and prop not in schema:
                    schema[prop] = p[prop]
            
            # Path params MUST be required=true
            norm = {
                "name": name, 
                "in": loc, 
                "required": True if loc == "path" else p.get("required", False), 
                "schema": schema
            }
            if "description" in p:
                norm["description"] = p["description"]
            if "x-suggested-name" in p:
                norm["x-suggested-name"] = p["x-suggested-name"]
            result.append(norm)
            
        # MISSING PATH PARAM INJECTION
        # If the endpoint path has /users/{id} but the LLM completely forgot to define 
        # the parameters array, or missed 'id', we MUST inject it to make it valid OpenAPI 3.0.
        for missing_path_param in path_params - seen_path_params:
            logger.info(f"Auto-injecting missing path parameter: '{missing_path_param}'")
            result.append({
                "name": missing_path_param,
                "in": "path",
                "required": True,
                "schema": {"type": "string"},
                "description": f"Auto-generated path parameter for {missing_path_param}"
            })
            
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
                
        # Handle invalid OpenAPI 3.0 type: "binary" 
        if schema.get("type") == "binary":
            schema["type"] = "string"
            schema["format"] = "binary"
            
        # Inline $ref since we don't have components defined
        if "$ref" in schema:
            ref_val = schema["$ref"]
            if not isinstance(ref_val, str):
                return {"type": "object"}
            type_name = ref_val.split("/")[-1].replace("[]", "")
            item_schema = {"type": "object", "description": f"Object of type {type_name}", "x-uncertain": True}
            if "[]" in ref_val:
                return {"type": "array", "items": item_schema}
            return item_schema
        
        # Opaque schema: type object/array with only a description and no properties/items
        # (e.g., already-inlined $refs). Mark as uncertain so the user knows it's a prediction.
        schema_type = schema.get("type")
        if (
            schema_type in ("object", "array")
            and "description" in schema
            and "properties" not in schema
            and "items" not in schema
            and "x-uncertain" not in schema
        ):
            schema["x-uncertain"] = True
        
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
        - Strips out any irregular keys that aren't 'default' or a valid 3-digit status code.
        
        See: https://swagger.io/specification/#responses-object
        """
        if not responses:
            return {"200": {"description": "Success"}}
        
        result = {}
        
        if isinstance(responses, dict):
            for k, v in responses.items():
                k_str = str(k)
                if k_str == 'default' or (k_str.isdigit() and 100 <= int(k_str) <= 599):
                    result[k_str] = self._normalize_response(v) if isinstance(v, dict) else {"description": "Response"}
                else:
                    logger.warning(f"Stripping invalid status code from responses: {k_str}")
        
        elif isinstance(responses, list):
            for r in responses:
                if isinstance(r, dict):
                    k_str = str(r.get("code", r.get("status", 200)))
                    if k_str == 'default' or (k_str.isdigit() and 100 <= int(k_str) <= 599):
                        result[k_str] = self._normalize_response(r)
        
        return result or {"200": {"description": "Success"}}
    
    def _normalize_response(self, r: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single Response Object. See: https://swagger.io/specification/#response-object"""
        res = {"description": r.get("description", "Response")}
        if "content" in r:
            if r["content"] is None:
                logger.error("Response content is null (None), skipping content generation.")
            else:
                content = {}
                for mt, obj in r["content"].items():
                    if isinstance(obj, dict):
                        schema = self._normalize_schema(obj.get("schema", {}))
                        # Drop content if schema is empty or carries no useful info
                        if self._is_empty_schema(schema):
                            continue
                        content[mt] = {"schema": schema}
                if content:
                    res["content"] = content
        elif "schema" in r:
            schema = self._normalize_schema(r["schema"])
            if not self._is_empty_schema(schema):
                res["content"] = {"application/json": {"schema": schema}}
        return res

    def _is_empty_schema(self, schema: Dict[str, Any]) -> bool:
        """
        Returns True if the schema carries no useful information:
        - Empty dict {}
        - Only contains x-uncertain with no description (purely a flag, nothing to show)
        - type: array with items that are themselves empty or only x-uncertain
        - type: object/array with no properties, no description (just a bare type)
        """
        if not schema:
            return True
        keys = set(schema.keys()) - {"x-uncertain"}
        if not keys:
            return True  # Only had x-uncertain flag, no content
        # type: array with no useful items
        if schema.get("type") == "array":
            items = schema.get("items")
            if items is None or items == {}:
                return True
        # type: object/array with empty properties
        if schema.get("type") == "object" and schema.get("properties") == {}:
            return True
        return False
    
    def validate(self, output: Dict[str, Any]) -> bool:
        """Validate that output has required OpenAPI 3.0 fields."""
        return all(f in output for f in ["openapi", "info", "paths"]) and \
               "title" in output.get("info", {}) and "version" in output.get("info", {})
