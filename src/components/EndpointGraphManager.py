import json
import os
import sqlite3
from haystack import component
from src.utils.logger import DocGenLogger
from src.utils.types import ASTOutputRecord
from typing import Dict, Set, List, Any, Optional
from src.utils.dependency_graph import DependencyGraph
from src.utils.weaviate_utils import get_node_id

logger = DocGenLogger(__name__)


@component
class EndpointGraphManager:
    """Manages independent graphs for each API endpoint."""

    def __init__(self, default_db_name: str = "dependencies.db"):
        self.endpoint_graphs: Dict[str, DependencyGraph] = {}
        self.default_db_name = default_db_name
        self.db_path = None

    def _init_db(self):
        """Initialize SQLite database for dependency tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS dependencies (
                        endpoint_id TEXT,
                        caller TEXT,
                        target TEXT,
                        UNIQUE(endpoint_id, caller, target)
                    )
                ''')
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to initialize SQLite database: {e}")

    def read_dependencies(self, endpoint_id: str = None) -> List[Dict[str, str]]:
        """Read dependencies from the database, optionally filtering by endpoint."""
        results = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if endpoint_id:
                    cursor.execute('SELECT endpoint_id, caller, target FROM dependencies WHERE endpoint_id = ?', (endpoint_id,))
                else:
                    cursor.execute('SELECT endpoint_id, caller, target FROM dependencies')

                for row in cursor.fetchall():
                    results.append({
                        "endpoint_id": row[0],
                        "caller": row[1],
                        "target": row[2]
                    })
        except Exception as e:
            logger.error(f"Failed to read dependencies from DB: {e}")
        return results

    def write_dependency(self, endpoint_id: str, caller: str, target: str) -> bool:
        """Write a single dependency edge to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO dependencies (endpoint_id, caller, target)
                    VALUES (?, ?, ?)
                ''', (endpoint_id, caller, target))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to write dependency to DB: {e}")
            return False

    def delete_dependency(self, endpoint_id: str, caller: str, target: str) -> bool:
        """Delete a single dependency edge from the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM dependencies 
                    WHERE endpoint_id = ? AND caller = ? AND target = ?
                ''', (endpoint_id, caller, target))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to delete dependency from DB: {e}")
            return False

    def get_affected_endpoints(self, changed_dependencies: List[str]) -> List[str]:
        """
        Retrieves all API endpoints affected by a change in one or more dependencies.
        """
        if not changed_dependencies:
            return []

        affected_endpoints = set()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                placeholders = ','.join(['?'] * len(changed_dependencies))
                query = f'''
                    SELECT DISTINCT endpoint_id 
                    FROM dependencies 
                    WHERE caller IN ({placeholders}) OR target IN ({placeholders})
                '''
                params = changed_dependencies * 2
                cursor.execute(query, params)
                for row in cursor.fetchall():
                    affected_endpoints.add(row[0])
        except Exception as e:
            logger.error(f"Failed to query affected endpoints from DB: {e}")
        return list(affected_endpoints)

    def _clear_endpoint_db(self, endpoint_id: str):
        """Clear all previous DB entries for a given endpoint."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM dependencies WHERE endpoint_id = ?', (endpoint_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to clear endpoint {endpoint_id} from DB: {e}")

    def _sync_graph_to_db(self, endpoint_id: str, graph: DependencyGraph):
        """Sync in-memory graph to SQLite."""
        self._clear_endpoint_db(endpoint_id)
        for caller, targets in graph.forward_graph.items():
            for target in targets:
                self.write_dependency(endpoint_id, caller, target)

    @component.output_types(endpoint_graphs=Dict[str, Any])
    def run(
        self,
        endpoints: Optional[List[ASTOutputRecord]] = None,
        project_name: str = "",
        files: Optional[List[Dict[str, Any]]] = None,
        code_chunks: Optional[List[ASTOutputRecord]] = None,
        wait_for_weaviate: Optional[int] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build dependency graphs for each endpoint using FilesAnalyzer output,
        resolving node_ids exactly via Weaviate get_node_id and AST records.
        """
        output_dir = os.path.join("output", project_name)
        os.makedirs(output_dir, exist_ok=True)
        self.db_path = os.path.join(output_dir, self.default_db_name)
        self._init_db()

        if not files or not endpoints:
            logger.warning("No endpoints or files provided to EndpointGraphManager")
            return {"endpoint_graphs": {}}

        return self._build_graphs(files, endpoints, code_chunks or [])

    def _build_graphs(
        self, 
        files: List[Dict[str, Any]], 
        endpoints: List[ASTOutputRecord], 
        code_chunks: List[ASTOutputRecord]
    ) -> Dict[str, Dict[str, Any]]:
        self.endpoint_graphs = {}

        # 1. Build AST catalogs to resolve missing origin/file_name from FilesAnalyzer
        ast_by_file_method = {}   # (f_name, m_name) -> node_id, class_name
        ast_by_class_method = {}  # (c_name, m_name) -> node_id

        for record in endpoints + code_chunks:
            file_name_val = record.get("file_path") or record.get("file_name")
            m_name_val = record.get("method_name")
            
            if not file_name_val or not m_name_val:
                logger.warning(f"Skipping AST record due to missing file_name or method_name: {record}")
                continue
                
            original_f_name = os.path.basename(file_name_val)
            f_name = original_f_name.lower()
            
            c_name_val = record.get("class_name") or "Global"
            c_name = c_name_val.lower()
            m_name = m_name_val.lower()
            
            node_id = get_node_id(
                file_name=original_f_name, 
                class_name=c_name_val, 
                method_name=m_name_val
            )
            
            ast_by_file_method[(f_name, m_name)] = {
                "node_id": node_id,
                "class_name": c_name_val
            }
                
            ast_by_class_method[(c_name, m_name)] = node_id

        # 2. Process FilesAnalyzer output to map each known node_id to its dependencies
        analyzer_deps: Dict[str, List[str]] = {}
        files_analyzer_catalog: Dict[tuple[str, str], str] = {} # (origin.lower(), name.lower()) -> node_id
        raw_deps_map: Dict[str, List[Dict[str, Any]]] = {}      # node_id -> raw dependencies
        
        # Pass A: generate all node_ids for filesAnalyzer items and build the catalog
        for file_info in files:
            file_path = file_info.get("file_path")
            if not file_path:
                logger.warning(f"Skipping filesAnalyzer file due to missing file_path: {file_info}")
                continue
                
            f_name = os.path.basename(file_path).lower()
            original_f_name = os.path.basename(file_path)

            for item in file_info.get("content", []):
                item_name = item.get("name")
                if not item_name:
                    logger.warning(f"Skipping filesAnalyzer item due to missing method_name in {file_path}")
                    continue
                    
                m_name = item_name.lower()
                
                ast_info = ast_by_file_method.get((f_name, m_name))
                if ast_info:
                    curr_node_id = ast_info["node_id"]
                else:
                    # Fallback if NOT found in AST chunks
                    origin = item.get("origin") or "Global"
                    
                    method_type = "unknown"
                    is_api = item.get("is_api_method")
                    if is_api and isinstance(is_api, dict):
                        method_type = is_api.get("method_type", "unknown")
                        
                    curr_node_id = get_node_id(original_f_name, origin, item_name)

                # Register in catalog by (origin, name)
                item_origin = item.get("origin") or "Global"
                files_analyzer_catalog[(item_origin.lower(), m_name)] = curr_node_id
                
                # Store raw dependencies for Pass B
                raw_deps_map[curr_node_id] = item.get("dependencies", [])
                
        # Pass B: resolve dependencies using the catalog exclusively
        for curr_node_id, raw_deps in raw_deps_map.items():
            deps = []
            for dep in raw_deps:
                dep_origin = dep.get("dependency_origin") or "Global"
                dep_name = dep.get("dependency_name")
                
                if not dep_name:
                    continue # Skip invalid dependencies
                    
                dep_type = dep.get("dependency_type")
                
                dep_c_name = dep_origin.lower()
                dep_m_name = dep_name.lower()
                
                # Resolve Target Node ID exclusively within the filesAnalyzer items
                target_node_id = files_analyzer_catalog.get((dep_c_name, dep_m_name))
                
                if target_node_id:
                    deps.append(target_node_id)
                else:
                    logger.debug(f"Dependency {dep_origin}:{dep_name} not found in analyzed files. Skipping.")
            
            analyzer_deps[curr_node_id] = deps

        # 3. Traverse from each Endpoint as root
        for ep in endpoints:
            file_name_val = ep.get('file_name')
            m_name_val = ep.get('method_name')
            
            if not file_name_val or not m_name_val:
                logger.warning(f"Skipping root endpoint due to missing file_name or method_name: {ep}")
                continue
                
            ep_node_id = get_node_id(
                file_name=file_name_val, 
                class_name=ep.get('class_name') or 'Global', 
                method_name=m_name_val
            )
            
            graph = DependencyGraph(start_node=ep_node_id)
            visited = set()
            queue = [ep_node_id]
            
            while queue:
                curr = queue.pop(0)
                if curr in visited:
                    continue
                visited.add(curr)
                
                deps = analyzer_deps.get(curr, [])
                graph.update_dependencies(curr, deps)
                
                for d in deps:
                    if d not in visited:
                        queue.append(d)
                        
            self.endpoint_graphs[ep_node_id] = graph
            self._sync_graph_to_db(ep_node_id, graph)

        logger.info(f"Built {len(self.endpoint_graphs)} endpoint graphs")
        return {"endpoint_graphs": self.endpoint_graphs}
