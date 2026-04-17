import os
import logging
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore

logger = logging.getLogger(__name__)

DEFAULT_WEAVIATE_URL = "http://127.0.0.1:8080"


def resolve_weaviate_url(config: dict) -> str:
    """
    Resolve the Weaviate URL from a config dict.

    Handles three failure modes:
      1. Key missing entirely  ->  returns default
      2. Key present but empty string (env var not set)  ->  returns default
      3. Key holds an unexpanded placeholder like "${WEAVIATE_URL}"  ->  returns default
    """
    raw = config.get("WEAVIATE_URL", "")
    if not raw or raw.startswith("${"):
        return DEFAULT_WEAVIATE_URL
    return raw


class WeaviateStore:
    _store = None
    _pid = None  # Crucial for Celery/FastAPI process safety

    @classmethod
    def get_store(cls, url: str = "http://127.0.0.1:8080", **kwargs) -> WeaviateDocumentStore:
        """
        Returns a process-safe, persistent WeaviateDocumentStore instance.
        """
        curr_pid = os.getpid()
        
        # If the store hasn't been created, or we are in a new fork (Celery)
        if cls._store is None or cls._pid != curr_pid:
            
            # Clean up the 'zombie' reference from the parent process if it exists
            # NOTE: We do NOT call cls.close() here because if we are in a child process
            # closing the inherited store might close the shared socket in the parent.
            # We simply discard the reference and re-initialize.
            if cls._store is not None:
                logger.info(f"Process ID changed from {cls._pid} to {curr_pid}. Discarding inherited WeaviateStore.")
                cls._store = None
            
            logger.info(f"Initializing WeaviateStore for process ID: {curr_pid}")
            
            # Final safety check on URL
            if not url or not (url.startswith("http://") or url.startswith("https://")):
                logger.warning(f"Invalid Weaviate URL '{url}', falling back to local default")
                url = "http://127.0.0.1:8080"

            # This is the actual initialization
            cls._store = WeaviateDocumentStore(url=url, **kwargs)
            cls._pid = curr_pid
            
        return cls._store

    @classmethod
    def close(cls):
        """Explicitly closes the connection."""
        try:
            if cls._store:
                # Close the underlying Weaviate client
                if hasattr(cls._store, "_client") and hasattr(cls._store._client, "close"):
                    cls._store._client.close()
                elif hasattr(cls._store, "close"):
                    cls._store.close()
        except Exception as e:
            logger.error(f"Error closing WeaviateStore: {e}")
        finally:
            cls._store = None
            cls._pid = None