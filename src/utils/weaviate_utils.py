"""
Weaviate utility functions for querying documents with filters.

This module provides reusable functions for querying Weaviate document store
with exact match filters on metadata fields.
"""

from typing import List, Optional
from haystack.dataclasses import Document
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
import logging

logger = logging.getLogger(__name__)


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
