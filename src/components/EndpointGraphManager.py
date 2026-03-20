"""
EndpointGraphManager - Haystack component for managing dependency graphs
and persisting them to a lightweight SQLite database.

Updated to work with AST-extracted endpoints from ControllerExtractor
and resolve dependencies via Weaviate code chunks.
"""
from haystack import component
from typing import Dict, Set, List, Any, Optional
import json
import sqlite3
import os
import re
from src.utils.dependency_graph import DependencyGraph
from src.utils.logger import DocGenLogger

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

    def _create_node_id(self, file_path: str, origin: str, name: str, method_type: str = "unknown") -> str:
        """Create a unique composite key: file_name:origin:name:method_type"""
        file_name = os.path.basename(file_path) if file_path else "unknown_file"
        origin_str = origin if origin else "unknown_origin"
        name_str = name if name else "unknown_name"
        method_str = method_type if method_type else "unknown"
        return f"{file_name}:{origin_str}:{name_str}:{method_str}"

    @component.output_types(endpoint_graphs=Dict[str, Any])
    def run(
        self,
        endpoints: Optional[List[Dict[str, Any]]] = None,
        project_name: str = "",
        files: Optional[List[Dict[str, Any]]] = None,
        code_chunks: Optional[Any] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """
        Build dependency graphs for each endpoint.

        Supports two modes:
        1. AST mode: receives `endpoints` from ControllerExtractor
        2. Legacy mode: receives `files` from FilesAnalyzer

        Args:
            endpoints: flat list of endpoint dicts from ControllerExtractor
            project_name: project name for DB path
            files: legacy FilesAnalyzer output
            code_chunks: code chunk documents (unused directly, but triggers DAG ordering)
        """
        # Set up project-specific DB path
        output_dir = os.path.join("output", project_name)
        os.makedirs(output_dir, exist_ok=True)
        self.db_path = os.path.join(output_dir, self.default_db_name)
        self._init_db()

        # --- AST-based mode (new) ---
        if endpoints:
            return self._run_ast_mode(endpoints)

        # --- Legacy mode (FilesAnalyzer) ---
        if files:
            return self._run_legacy_mode(files)

        logger.warning("No endpoints or files provided to EndpointGraphManager")
        return {"endpoint_graphs": {}}

    def _run_ast_mode(self, endpoints: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Build graphs from AST-extracted endpoints."""
        for ep in endpoints:
            endpoint_id = ep.get("node_id") or self._create_node_id(
                ep.get("file_path", ""), ep.get("class_name", ""), ep.get("method_name", ""), ep.get("method_type", "unknown")
            )

            graph = DependencyGraph(start_node=endpoint_id)

            # Extract references from LLM output
            raw_deps = ep.get("dependencies", [])

            # Add each reference as a dependency edge
            for ref in raw_deps:
                # Handle both string references and dict-based dependencies
                if isinstance(ref, dict):
                    target_id = self._parse_dependency_id(ref, ep.get("file_path", ""))
                elif isinstance(ref, str):
                    try:
                        parsed = json.loads(ref)
                        target_id = self._parse_dependency_id(parsed, ep.get("file_path", ""))
                    except Exception:
                        target_id = ref
                else:
                    target_id = str(ref)
                
                graph.add_dependency(endpoint_id, target_id)

            self.endpoint_graphs[endpoint_id] = graph
            self._sync_graph_to_db(endpoint_id, graph)

        logger.info(f"Built {len(self.endpoint_graphs)} endpoint graphs (AST mode)")
        return {"endpoint_graphs": self.endpoint_graphs}

    def _run_legacy_mode(self, files: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Build graphs from legacy FilesAnalyzer output."""
        all_components = {}
        name_index: Dict[str, str] = {}
        endpoint_ids = []

        for file_info in files:
            file_path = file_info.get("file_path", "")
            content = file_info.get("content", [])

            for item in content:
                name = item.get("name")
                if not name:
                    continue

                origin = item.get("class_name", item.get("type", ""))
                component_id = self._create_node_id(file_path, origin, name)

                item_with_context = item.copy()
                item_with_context["_source_file_path"] = file_path
                all_components[component_id] = item_with_context
                name_index[name] = component_id

                if item.get("is_api_method") and str(item.get("type", "")).lower() == "function":
                    endpoint_ids.append(component_id)

        for endpoint_id in endpoint_ids:
            graph = DependencyGraph(start_node=endpoint_id)
            self.endpoint_graphs[endpoint_id] = graph
            self._populate_subgraph(graph, endpoint_id, all_components, name_index, set())
            self._sync_graph_to_db(endpoint_id, graph)

        return {"endpoint_graphs": self.endpoint_graphs}

    def _resolve_dependency(self, dep: Any, name_index: Dict[str, str], current_file_path: str) -> str:
        """Resolve a dependency to the actual indexed component ID."""
        dep_name = None
        if isinstance(dep, dict):
            dep_name = dep.get('dependency_name', '')
        elif isinstance(dep, str):
            try:
                parsed = json.loads(dep)
                dep_name = parsed.get('dependency_name', '')
            except Exception:
                dep_name = dep

        if dep_name and dep_name in name_index:
            return name_index[dep_name]

        return self._parse_dependency_id(dep, current_file_path)

    def _parse_dependency_id(self, dep: Any, current_file_path: str) -> str:
        """Parse a dependency object/string into the composite node ID."""
        if isinstance(dep, dict):
            file_path = dep.get('file_path', current_file_path)
            return self._create_node_id(file_path, dep.get('dependency_origin', ''), dep.get('dependency_name', ''), dep.get('method_type', 'unknown'))
        elif isinstance(dep, str):
            try:
                parsed = json.loads(dep)
                file_path = parsed.get('file_path', current_file_path)
                return self._create_node_id(file_path, parsed.get('dependency_origin', ''), parsed.get('dependency_name', ''), parsed.get('method_type', 'unknown'))
            except Exception:
                return self._create_node_id(current_file_path, "unknown_origin", dep)
        return str(dep)

    def _populate_subgraph(
        self,
        graph: DependencyGraph,
        current_node_id: str,
        all_components: Dict[str, Any],
        name_index: Dict[str, str],
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
        string_deps = [self._resolve_dependency(d, name_index, source_file_path) for d in raw_deps]
        graph.update_dependencies(current_node_id, string_deps)

        for target_id in string_deps:
            self._populate_subgraph(graph, target_id, all_components, name_index, visited)
