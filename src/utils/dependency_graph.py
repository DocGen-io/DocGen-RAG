"""
Dependency Graph - High-performance data structure for tracking API dependencies.
"""
from typing import Dict, Set, List
import json

class DependencyGraph:
    """
    Directed Graph to track dependencies originating from a single API method.
    Uses Maps of Sets for O(1) lookups and lightning-fast updates.
    """
    
    def __init__(self, start_node: str):
        self.start_node = start_node
        # Tracks what a node calls (Adjacency List)
        self.forward_graph: Dict[str, Set[str]] = {}
        # Tracks who calls a node (In-Degree tracking)
        self.reverse_graph: Dict[str, Set[str]] = {}
        
        # Ensure the start node always exists
        self.forward_graph[start_node] = set()
        self.reverse_graph[start_node] = set()

    def add_dependency(self, caller: str, target: str) -> None:
        """Adds a directed edge from caller to target in O(1) time."""
        if caller not in self.forward_graph:
            self.forward_graph[caller] = set()
        if target not in self.forward_graph:
            self.forward_graph[target] = set()
            
        if caller not in self.reverse_graph:
            self.reverse_graph[caller] = set()
        if target not in self.reverse_graph:
            self.reverse_graph[target] = set()

        self.forward_graph[caller].add(target)
        self.reverse_graph[target].add(caller)

    def remove_dependency(self, caller: str, target: str) -> None:
        """
        Removes an edge in O(1) time.
        CRITICAL: If the target has 0 incoming edges (orphaned), it is deleted completely.
        """
        if caller in self.forward_graph and target in self.forward_graph[caller]:
            self.forward_graph[caller].remove(target)
            
        if target in self.reverse_graph and caller in self.reverse_graph[target]:
            self.reverse_graph[target].remove(caller)
            
            # If target has 0 incoming edges and is NOT the API start node, delete it.
            if not self.reverse_graph[target] and target != self.start_node:
                self._remove_node(target)

    def _remove_node(self, node: str) -> None:
        """Deep clean removal of an orphaned node and cascaded removal of its dependencies."""
        if node in self.forward_graph:
            # List constructor avoids dictionary changing size during iteration
            outgoing_targets = list(self.forward_graph[node])
            for target in outgoing_targets:
                self.remove_dependency(node, target)
            del self.forward_graph[node]
            
        if node in self.reverse_graph:
            del self.reverse_graph[node]

    def update_dependencies(self, caller: str, new_dependencies: List[str]) -> None:
        """
        Handles lightning-fast updates when a file changes using Set calculus.
        """
        old_dependencies = self.forward_graph.get(caller, set())
        new_deps_set = set(new_dependencies)
        
        to_add = new_deps_set - old_dependencies
        to_remove = old_dependencies - new_deps_set
        
        for target in to_add:
            self.add_dependency(caller, target)
            
        for target in list(to_remove):
            self.remove_dependency(caller, target)
            
    def get_all_nodes(self) -> Set[str]:
        """Utility to retrieve all active nodes in this specific graph."""
        return set(self.forward_graph.keys())
