
from src.utils.weaviateStore import WeaviateStore
from src.utils.config_loader import load_config
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

def cleanup_weaviate():
    """
    Clears all existing documents with doc_type='endpoint_documentation' from Weaviate.
    This allows a fresh start with stable IDs and no duplicates.
    """
    config = load_config("config.yaml")
    url = config.get("WEAVIATE_URL", "http://127.0.0.1:8080")
    store = WeaviateStore.get_store(url=url)
    
    logger.info(f"Connecting to Weaviate at {url}")
    
    # Query for all endpoint documentation docs
    docs = store.filter_documents(
        filters={"field": "meta.doc_type", "operator": "==", "value": "endpoint_documentation"}
    )
    
    if not docs:
        logger.info("No endpoint documentation docs found to clean up.")
        return

    doc_ids = [doc.id for doc in docs]
    logger.info(f"Found {len(doc_ids)} docs to delete.")
    
    try:
        store.delete_documents(document_ids=doc_ids)
        logger.info("Successfully deleted all endpoint documentation docs.")
    except Exception as e:
        logger.error(f"Failed to delete documents: {e}")

if __name__ == "__main__":
    cleanup_weaviate()
