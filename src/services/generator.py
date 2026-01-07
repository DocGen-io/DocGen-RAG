import json
import os
import time
from typing import Dict, List, Any
from src.core.config import settings
from src.core.security import SecurityAnalyzer

class DocGenerator:
    """
    Generates the final documentation artifacts: Swagger.json, examples.ts, Postman Collection.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_base = output_dir

    def create_output_folder(self) -> str:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join(self.output_base, timestamp)
        os.makedirs(path, exist_ok=True)
        return path

    def generate_artifacts(self, extracted_data: List[Dict[str, Any]], project_security_alerts: List[str] = []) -> Dict[str, str]:
        """
        Takes extracted API data (list of endpoints with details) and generates files.
        """
        output_path = self.create_output_folder()
        
        # 1. Swagger / OpenAPI Generation
        swagger = self._build_swagger(extracted_data, project_security_alerts)
        swagger_path = os.path.join(output_path, "swagger.json")
        with open(swagger_path, "w") as f:
            json.dump(swagger, f, indent=2)

        # 2. Postman Collection
        postman = self._build_postman(extracted_data)
        postman_path = os.path.join(output_path, "postman_collection.json")
        with open(postman_path, "w") as f:
            json.dump(postman, f, indent=2)

        # 3. Examples.ts
        examples_content = self._build_examples_ts(extracted_data)
        examples_path = os.path.join(output_path, "examples.ts")
        with open(examples_path, "w") as f:
            f.write(examples_content)

        return {
            "swagger": swagger_path,
            "postman": postman_path,
            "examples": examples_path
        }

    def _build_swagger(self, data: List[Dict], alerts: List[str]) -> Dict:
        paths = {}
        for item in data:
            # Grouping Logic: users/{id} -> group 'users'
            # We assume 'item' has 'path', 'method', 'description', 'parameters', etc.
            path = item.get("path", "/")
            method = item.get("method", "get").lower()
            
            # Security Analysis per endpoint
            endpoint_alerts = SecurityAnalyzer.analyze_endpoint(path, method)
            description = item.get("description", "")
            if endpoint_alerts:
                description += "\n\n" + "\n".join([f"WARNING: {a}" for a in endpoint_alerts])

            if path not in paths:
                paths[path] = {}
            
            paths[path][method] = {
                "summary": f"{method.upper()} {path}",
                "description": description,
                "tags": [path.strip("/").split("/")[0]] if path != "/" else ["root"],
                "responses": {
                    "200": {"description": "Successful response"}
                }
            }
        
        return {
            "openapi": "3.0.0",
            "info": {
                "title": settings.config["app"].get("APP_NAME", "Generated API"),
                "version": "1.0.0",
                "description": "Automatically generated documentation.\n" + "\n".join(alerts)
            },
            "paths": paths
        }

    def _build_postman(self, data: List[Dict]) -> Dict:
        # Simplified Postman generation
        item_list = []
        for d in data:
            item_list.append({
                "name": d.get("path"),
                "request": {
                    "method": d.get("method", "GET").upper(),
                    "url": {
                        "raw": "{{base_url}}" + d.get("path"),
                        "host": ["{{base_url}}"],
                        "path": d.get("path").strip("/").split("/")
                    }
                }
            })
            
        return {
            "info": {"name": "Generated Collection", "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"},
            "item": item_list
        }

    def _build_examples_ts(self, data: List[Dict]) -> str:
        # Generates a TS file with exported JSON objects
        ts_content = "/** Auto-generated API Examples */\n\n"
        
        examples_map = {}
        for d in data:
            # unique key: method_path
            key = f"{d.get('method', 'get').lower()}_{d.get('path', '').strip('/').replace('/', '_')}"
            # Clean key
            key = key.replace("{", "").replace("}", "")
            
            examples_map[key] = {
                "request": d.get("example_request", {}),
                "response": d.get("example_response", {})
            }
            
        ts_content += f"export const apiExamples = {json.dumps(examples_map, indent=2)};\n"
        return ts_content
