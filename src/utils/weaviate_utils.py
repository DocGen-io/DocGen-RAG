"""
Weaviate utility functions for querying documents with filters.

This module provides reusable functions for querying Weaviate document store
with exact match filters on metadata fields.
"""

from typing import List, Optional
from haystack.dataclasses import Document
from haystack_integrations.document_stores.weaviate import WeaviateDocumentStore
from .logger import DocGenLogger
from .tenant_context import get_tenant
from weaviate.classes.tenants import Tenant
import weaviate.collections.collection.sync

# Weaviate's `Collection` does not implement `__bool__`. In Python, truthiness (`if obj:`) 
# then falls back to `__len__()`, which triggers a GRPC `aggregate` query.
# Haystack uses `if self._collection:` extensively, causing silent network calls and
# crashing with multi-tenant collections since no tenant is scoped yet.
# We patch `__bool__` globally to return True to prevent this.
weaviate.collections.collection.sync.Collection.__bool__ = lambda self: True

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


def get_node_id(file_name: str, class_name: str, method_name: str="none") -> str:
    return f"{file_name.lower()}:{class_name.lower()}:{method_name.lower()}"

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
import threading

_SHARED_STORES = {}
_store_lock = threading.Lock()

@contextmanager
def get_weaviate_store(url: str = "http://127.0.0.1:8080", **kwargs):
    """
    Context manager for WeaviateDocumentStore with automatic tenant isolation.
    Uses a process-global connection cache to prevent `WeaviateClosedClientError`
    caused by __del__ garbage collection closing the shared HTTP pool.
    """
    team_id = get_tenant()
    cache_key = (url, team_id)

    with _store_lock:
        if cache_key not in _SHARED_STORES:
            # Enable multi-tenancy on the collection when a tenant is active
            if team_id:
                collection_settings = kwargs.pop("collection_settings", None) or {}
                collection_settings.setdefault("multiTenancyConfig", {"enabled": True})
                kwargs["collection_settings"] = collection_settings

            store = WeaviateDocumentStore(url=url, **kwargs)
            
            # Scope all reads/writes to the team's tenant shard
            if team_id:
                _ensure_tenant(store, team_id)
                # Replace the collection reference with a tenant-scoped one
                store._collection = store.collection.with_tenant(team_id)
                
            # Monkey-patch _batch_write to avoid global client.batch.dynamic() which breaks multi-tenancy via list_all()
            def patched_batch_write(documents):
                from haystack.document_stores.errors import DocumentStoreError
                from weaviate.classes.query import Filter
                from weaviate.util import generate_uuid5
                import weaviate.classes as wvc
                
                if not documents:
                    return 0
                    
                uuids = [generate_uuid5(doc.id) for doc in documents]
                try:
                    store.collection.data.delete_many(where=Filter.by_id().contains_any(uuids))
                except Exception as e:
                    logger.warning(f"Error during delete_many: {e}")

                data_objects = []
                for doc in documents:
                    import base64
                    props = doc.to_dict()
                    props["_original_id"] = props.pop("id")
                    if (blob := props.pop("blob")) is not None:
                        props["blob_data"] = base64.b64encode(bytes(blob.pop("data"))).decode()
                        props["blob_mime_type"] = blob.pop("mime_type")
                    del props["embedding"]
                    props.pop("sparse_embedding", None)

                    data_objects.append(
                        wvc.data.DataObject(
                            properties=props,
                            uuid=generate_uuid5(doc.id),
                            vector=doc.embedding,
                        )
                    )
                
                result = store.collection.data.insert_many(data_objects)
                if result.has_errors:
                    err_msg = "".join([f"Err: {str(val.message)}; " for key, val in result.errors.items()])
                    raise DocumentStoreError(f"Failed to batch write: {err_msg}")
                    
                return len(documents)
                
            store._batch_write = patched_batch_write
                
            _SHARED_STORES[cache_key] = store

    store = _SHARED_STORES[cache_key]
    
    yield store
    
    # We DO NOT close or delete the store here. It is cached globally for the 
    # lifetime of the worker process to maintain the active HTTP connection pool.


def _ensure_tenant(store: WeaviateDocumentStore, team_id: str) -> None:
    """Create the tenant shard in Weaviate if it doesn't already exist."""
    try:
        existing = {t.name for t in store.collection.tenants.get().values()}
        if team_id not in existing:
            store.collection.tenants.create([Tenant(name=team_id)])
            logger.info(f"Created Weaviate tenant shard for team '{team_id}'")
    except Exception as e:
        logger.warning(f"Could not ensure tenant '{team_id}': {e}")
