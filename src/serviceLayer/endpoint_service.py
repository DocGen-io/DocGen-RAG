import json
from typing import Dict, Any, List, Optional
from src.utils.weaviate_utils import get_weaviate_store, extract_and_inject_node_id
from src.utils.rbac_utils import to_uuid
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

class EndpointService:
    """
    Service layer for interacting with endpoint metadata in Weaviate.
    Encapsulates database logic to keep workers and API routers clean.
    """

    def __init__(self, weaviate_url: str):
        self.weaviate_url = weaviate_url

    def fetch_project_endpoints(self, project_name: str, team_id: str) -> Dict[str, Dict[str, Any]]:
        """
        Retrieves all endpoint documentation nodes for a specific project and team.
        Returns a dictionary of paths mapped to their method definitions.
        """
        logger.info(f"Fetching endpoints for project={project_name}, team_id={team_id}")
        
        with get_weaviate_store(url=self.weaviate_url) as store:
            filters = {
                "operator": "AND",
                "conditions": [
                    {"field": "meta.doc_type", "operator": "==", "value": "endpoint_documentation"},
                    {"field": "meta.project_name", "operator": "==", "value": project_name},
                    {"field": "meta.team_id", "operator": "==", "value": to_uuid(team_id)}
                ]
            }
            
            try:
                docs = store.filter_documents(filters=filters)
            except Exception as e:
                logger.error(f"Weaviate filter_documents failed: {e}")
                return {}

            paths: Dict[str, Dict[str, Any]] = {}
            for doc in docs:
                raw_json_str = doc.meta.get("raw_json")
                if not raw_json_str:
                    logger.warning(f"Document {doc.id} missing raw_json metadata")
                    continue
                    
                try:
                    data = json.loads(raw_json_str)
                    path = data.get("path")
                    method = data.get("method", "get").lower()
                    
                    if path:
                        doc_id_str = str(doc.id)
                        if doc_id_str not in paths:
                            paths[doc_id_str] = {}
                        
                        lightweight_data = {
                            "summary": data.get("summary", ""),
                            "operationId": data.get("operationId", ""),
                            "path": path,
                            "method": method.upper()
                        }
                        
                        # Inject node_id using standard utility
                        lightweight_data = extract_and_inject_node_id(doc, lightweight_data, default_path=path, default_method=method.upper())
                            
                        paths[doc_id_str][method] = lightweight_data
                except Exception as e:
                    logger.warning(f"Failed to parse raw_json for document {doc.id}: {e}")
                    continue
            
            logger.info(f"Retrieved {len(paths)} unique paths for project={project_name}")
            return paths

    def fetch_endpoint(self, project_name: str, team_id: str, path: str, method: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single endpoint document by project, team, path and method.
        """
        logger.info(f"Fetching endpoint project={project_name}, path={path}, method={method}")
        
        with get_weaviate_store(url=self.weaviate_url) as store:
            filters = {
                "operator": "AND",
                "conditions": [
                    {"field": "meta.doc_type", "operator": "==", "value": "endpoint_documentation"},
                    {"field": "meta.project_name", "operator": "==", "value": project_name},
                    {"field": "meta.team_id", "operator": "==", "value": to_uuid(team_id)},
                    {"field": "meta.path", "operator": "==", "value": path},
                    {"field": "meta.method", "operator": "==", "value": method.lower()}
                ]
            }
            
            try:
                docs = store.filter_documents(filters=filters)
                if not docs:
                    logger.warning(f"No document found for endpoint {method.upper()} {path}")
                    return None
                    
                doc = docs[0]
                raw_json_str = doc.meta.get("raw_json")
                if not raw_json_str:
                    logger.error(f"Endpoint document {doc.id} missing raw_json")
                    return None
                    
                data = json.loads(raw_json_str)
                # Inject node_id using standard utility
                return extract_and_inject_node_id(doc, data, default_path=path, default_method=method.upper())
            except Exception as e:
                logger.error(f"Failed to fetch endpoint from Weaviate: {e}")
                return None


