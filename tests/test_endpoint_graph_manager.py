import pytest
import os
import sqlite3
from src.components.EndpointGraphManager import EndpointGraphManager

@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_dependencies.db")

@pytest.fixture
def graph_manager(temp_db_path):
    return EndpointGraphManager(db_path=temp_db_path)

@pytest.fixture
def populate_db(graph_manager):
    # Populate DB with some mocked endpoints and dependencies
    # endpoint1 -> dep1, dep2
    # endpoint2 -> dep2, dep3
    # endpoint3 -> dep4
    
    graph_manager.write_dependency("endpoint1", "endpoint1", "dep1")
    graph_manager.write_dependency("endpoint1", "dep1", "dep2")
    
    graph_manager.write_dependency("endpoint2", "endpoint2", "dep2")
    graph_manager.write_dependency("endpoint2", "dep2", "dep3")
    
    graph_manager.write_dependency("endpoint3", "endpoint3", "dep4")
    
    return True

def test_get_affected_endpoints_empty(graph_manager, populate_db):
    assert graph_manager.get_affected_endpoints([]) == []

def test_get_affected_endpoints_single_match(graph_manager, populate_db):
    affected = graph_manager.get_affected_endpoints(["dep1"])
    assert set(affected) == {"endpoint1"}
    
    affected = graph_manager.get_affected_endpoints(["dep3"])
    assert set(affected) == {"endpoint2"}

def test_get_affected_endpoints_multiple_matches(graph_manager, populate_db):
    affected = graph_manager.get_affected_endpoints(["dep2"])
    assert set(affected) == {"endpoint1", "endpoint2"}

def test_get_affected_endpoints_multiple_deps(graph_manager, populate_db):
    affected = graph_manager.get_affected_endpoints(["dep1", "dep4"])
    assert set(affected) == {"endpoint1", "endpoint3"}

def test_get_affected_endpoints_no_match(graph_manager, populate_db):
    affected = graph_manager.get_affected_endpoints(["non_existent_dep"])
    assert affected == []
