"""
EndpointGraphManager - Haystack component for managing dependency graphs
and persisting them to a lightweight SQLite database.
"""
from haystack import component
from typing import Dict, Set, List, Any
import json
import sqlite3
import os
from src.utils.dependency_graph import DependencyGraph
from src.utils.logger import DocGenLogger

logger = DocGenLogger(__name__)

@component
class EndpointGraphManager:
    """Manages independent graphs for each API endpoint found by filesAnalyzer."""
    
    def __init__(self, db_path: str = "dependencies.db"):
        # Maps endpoint method ID to its complete DependencyGraph
        self.endpoint_graphs: Dict[str, DependencyGraph] = {}
        self.db_path = db_path
        self._init_db()
        
    def _init_db(self):
        """Initialize SQLite database for dependency tracking."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Create dependencies table
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
        Retrieves all API endpoints that are affected by a change in one or more dependencies.
        It runs an efficient SQL query to find any endpoint where the changed dependency 
        appears as either a caller or a target.
        """
        if not changed_dependencies:
            return []
            
        affected_endpoints = set()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Parameterized query placeholders
                placeholders = ','.join(['?'] * len(changed_dependencies))
                
                query = f'''
                    SELECT DISTINCT endpoint_id 
                    FROM dependencies 
                    WHERE caller IN ({placeholders}) OR target IN ({placeholders})
                '''
                
                # Parameters are repeated twice: once for caller, once for target
                params = changed_dependencies * 2
                
                cursor.execute(query, params)
                
                for row in cursor.fetchall():
                    affected_endpoints.add(row[0])
                    
        except Exception as e:
            logger.error(f"Failed to query affected endpoints from DB: {e}")
            
        return list(affected_endpoints)
            
    def _clear_endpoint_db(self, endpoint_id: str):
        """Clear all previous DB entries for a given endpoint before full rebuild."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM dependencies WHERE endpoint_id = ?', (endpoint_id,))
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to clear endpoint {endpoint_id} from DB: {e}")

    def _sync_graph_to_db(self, endpoint_id: str, graph: DependencyGraph):
        """Sync the in-memory graph to the SQLite database."""
        self._clear_endpoint_db(endpoint_id)
        
        # graph.forward_graph dictates all out-edges
        for caller, targets in graph.forward_graph.items():
            for target in targets:
                self.write_dependency(endpoint_id, caller, target)

    def _create_node_id(self, file_path: str, origin: str, name: str) -> str:
        """Create a unique composite key: file_path:origin:name"""
        file_name = os.path.basename(file_path) if file_path else "unknown_file"
        origin_str = origin if origin else "unknown_origin"
        name_str = name if name else "unknown_name"
        return f"{file_name}:{origin_str}:{name_str}"
        
    def _parse_dependency_id(self, dep: Any, current_file_path: str) -> str:
        """Parse a dependency object/string into the composite node ID."""
        if isinstance(dep, dict):
            file_path = dep.get('file_path', current_file_path)
            return self._create_node_id(file_path, dep.get('dependency_origin', ''), dep.get('dependency_name', ''))
            
        elif isinstance(dep, str):
            try:
                parsed = json.loads(dep)
                file_path = parsed.get('file_path', current_file_path)
                return self._create_node_id(file_path, parsed.get('dependency_origin', ''), parsed.get('dependency_name', ''))
            except Exception:
                return self._create_node_id(current_file_path, "unknown_origin", dep)
        return str(dep)
        
    @component.output_types(endpoint_graphs=Dict[str, Any])
    def run(self, analyzed_files: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        Instantiates one graph per endpoint method and traverses dependencies.
        """
        all_components = {}
        endpoints = []
        
        # 1. First sweep to locate endpoints and index all components for fast lookup
        for file_info in analyzed_files:
            file_path = file_info.get("file_path", "")
            content = file_info.get("content", [])
            
            for item in content:
                name = item.get("name")
                if not name:
                    continue
                
                # Form composite ID
                origin = item.get("class_name", item.get("type", ""))
                component_id = self._create_node_id(file_path, origin, name)
                
                item_with_context = item.copy()
                item_with_context["_source_file_path"] = file_path
                all_components[component_id] = item_with_context
                
                if item.get("is_api_method"):
                    endpoints.append(component_id)
                    
        # 2. Build independent graphs for each endpoint method
        for endpoint_id in endpoints:
            graph = DependencyGraph(start_node=endpoint_id)
            self.endpoint_graphs[endpoint_id] = graph
            
            # DFS/BFS traverse through the stored components
            self._populate_subgraph(graph, endpoint_id, all_components, set())
            
            # 3. Sync to database
            self._sync_graph_to_db(endpoint_id, graph)
            
        return {"endpoint_graphs": self.endpoint_graphs}
            
    def _populate_subgraph(
        self, 
        graph: DependencyGraph, 
        current_node_id: str, 
        all_components: Dict[str, Any], 
        visited: Set[str]
    ) -> None:
        """Recursively pulls nested dependencies into the start node's graph."""
        if current_node_id in visited:
            return
            
        visited.add(current_node_id)
        
        item = all_components.get(current_node_id)
        if not item:
            return
            
        source_file_path = item.get("_source_file_path", "")
        raw_deps = item.get("dependencies", [])
        string_deps = [self._parse_dependency_id(d, source_file_path) for d in raw_deps]
        
        # Apply the fast graph update
        graph.update_dependencies(current_node_id, string_deps)
        
        # Recurse
        for target_id in string_deps:
            self._populate_subgraph(graph, target_id, all_components, visited)
