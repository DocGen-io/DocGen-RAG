import os
import yaml
from typing import Any, Dict, Optional

class Settings:
    _instance = None

    def __init__(self):
        self.config: Dict[str, Any] = {
            "rag": {
                "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
                "top_k_retriever": 10,
                "top_k_reranker": 5,
                "chunk_size": 500
            },
            "app": {
                "environment": "development"
            },
            # Core/Env vars
            "WEAVIATE_URL": os.getenv("WEAVIATE_URL", "http://127.0.0.1:8080"),
            "WEAVIATE_API_KEY": os.getenv("WEAVIATE_API_KEY", None),
            "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", None)
        }
        self.load_yaml()

    def load_yaml(self):
        yaml_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "settings.yml")
        if os.path.exists(yaml_path):
            with open(yaml_path, "r") as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config:
                    self.update_nested(self.config, yaml_config)

    def update_nested(self, d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = d.get(k, {})
                self.update_nested(d[k], v)
            else:
                d[k] = v

    def get(self, path: str, default=None):
        keys = path.split(".")
        val = self.config
        for k in keys:
            if isinstance(val, dict):
                val = val.get(k)
            else:
                return default
        return val if val is not None else default

    # Shortcuts for code readability
    @property
    def WEAVIATE_URL(self): return self.config["WEAVIATE_URL"]
    @property
    def OPENAI_API_KEY(self): return self.config["OPENAI_API_KEY"]
    @property
    def EMBEDDING_MODEL(self): return self.config["rag"]["embedding_model"]
    @property
    def RERANKER_MODEL(self): return "cross-encoder/ms-marco-MiniLM-L-6-v2" # Hardcoded backup or from yaml

settings = Settings()
