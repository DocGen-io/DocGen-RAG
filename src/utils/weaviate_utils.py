"""
Weaviate utility functions for querying documents with filters.

This module provides reusable functions for querying Weaviate document store
with exact match filters on metadata fields.
"""

from typing import List, Optional, Dict, Any
from haystack.dataclasses import Document
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from .logger import DocGenLogger

logger = DocGenLogger(__name__)


def fetch_by_method_name(
    document_store: WeaviateDocumentStore,
    method_name: str,
    doc_type: str = "ast_method"
) -> List[Document]:
    """
    Query Weaviate for documents matching exact method name.
    
    Args:
        document_store: WeaviateDocumentStore instance
        method_name: Exact method name to search for
        doc_type: Document type filter (default: "ast_method")
        
    Returns:
        List of matching Document objects
    """
    filters = {
        "operator": "AND",
        "conditions": [
            {"field": "meta.type", "operator": "==", "value": doc_type},
            {"field": "meta.method_name", "operator": "==", "value": method_name}
        ]
    }
    
    try:
        documents = document_store.filter_documents(filters=filters)
        logger.debug(f"Found {len(documents)} documents for method: {method_name}")
        return documents
    except Exception as e:
        logger.error(f"Error fetching documents for method {method_name}: {e}")
        return []



def get_node_id(
    file_name: str, 
    class_name: str, 
    method_name: str = "none",
    api_details: Optional[Dict[str, Any]] = None
) -> str:
    """
    Generate a unique node ID, optionally namespaced by team/project/job context.
    
    Args:
        file_name: Originating file name
        class_name: Class name or 'API'
        method_name: Method or endpoint path
        api_details: Optional context dictionary or dataclass (APIDetailsRecord)
    """
    base = f"{str(file_name).lower()}:{str(class_name).lower()}:{str(method_name).lower()}"
    
    if api_details:
        # Extract namespace markers from api_details (dict or object)
        ns_parts = []
        for key in ["team_id", "project_name", "job_id"]:
            val = None
            if isinstance(api_details, dict):
                val = api_details.get(key)
            else:
                val = getattr(api_details, key, None)
            
            if val:
                ns_parts.append(str(val))
        
        if ns_parts:
            return f"{base}:{':'.join(ns_parts)}"
            
    return base

def fetch_by_class_name(
    document_store: WeaviateDocumentStore,
    class_name: str,
    doc_type: str = "ast_method"
) -> List[Document]:
    """
    Query Weaviate for documents matching exact class name.
    
    Args:
        document_store: WeaviateDocumentStore instance
        class_name: Exact class name to search for
        doc_type: Document type filter (default: "ast_method")
        
    Returns:
        List of matching Document objects
    """
    filters = {
        "operator": "AND",
        "conditions": [
            {"field": "meta.type", "operator": "==", "value": doc_type},
            {"field": "meta.class_name", "operator": "==", "value": class_name}
        ]
    }
    
    try:
        documents = document_store.filter_documents(filters=filters)
        logger.debug(f"Found {len(documents)} documents for class: {class_name}")
        return documents
    except Exception as e:
        logger.error(f"Error fetching documents for class {class_name}: {e}")
        return []

def fetch_by_node_id(
    document_store: WeaviateDocumentStore,
    node_id: str
) -> List[Document]:
    """
    Query Weaviate for documents matching exact composite node ID.
    
    Args:
        document_store: WeaviateDocumentStore instance
        node_id: Exact node_id to search for (format: file_name:origin:name)
        
    Returns:
        List of matching Document objects
    """
    filters = {
        "field": "meta.node_id",
        "operator": "==",
        "value": node_id
    }
    
    try:
        documents = document_store.filter_documents(filters=filters)
        logger.debug(f"Found {len(documents)} documents for node_id: {node_id}")
        return documents
    except Exception as e:
        logger.error(f"Error fetching documents for node_id {node_id}: {e}")
        return []

from contextlib import contextmanager

@contextmanager
def get_weaviate_store(url: str = "http://127.0.0.1:8080", **kwargs):
    """
    Context manager to initialize and automatically close WeaviateDocumentStore.
    Produces DRY, reliable connection handling.
    """
    store = WeaviateDocumentStore(url=url, **kwargs)
    try:
        yield store
    finally:
        try:
            # Explicitly close the connection to stop the ResourceWarnings
            if hasattr(store, "_client") and hasattr(store._client, "close"):
                store._client.close()
            elif hasattr(store, "close"):
                store.close()
        except Exception as e:
            logger.error(f"Failed to close WeaviateDocumentStore: {e}")
