"""
Unit tests for DocumentationCreator component handling EndpointGraphManager inputs.
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, call
from haystack.dataclasses import Document
from src.components.DocumentationCreator import DocumentationCreator
from src.utils.dependency_graph import DependencyGraph
from src.utils.llm_json_handler import LLMJsonHandler
from src.utils.weaviate_utils import fetch_by_node_id

class TestDocumentationCreatorInput:
    """Test how DocumentationCreator handles its new inputs."""

    def test_run_with_no_graphs(self):
        with patch.object(DocumentationCreator, '__init__', lambda self: None):
            creator = DocumentationCreator()
            creator.output_dir = "temp"
            result = creator.run(endpoint_graphs={})
            assert result["methods_processed"] == 0
            assert result["methods_failed"] == 0
            assert result["output_files"] == {}

class TestDocumentationCreatorContextFetching:
    """Tests for traversing EndpointGraphs and fetching from Weaviate."""
    
    @patch('src.components.DocumentationCreator.fetch_by_node_id')
    def test_graph_traversal_and_fetching(self, mock_fetch):
        # Create a mock DependencyGraph
        graph = DependencyGraph("controller.ts:TestController:myEndpoint")
        graph.add_dependency("controller.ts:TestController:myEndpoint", "service.ts:TestService:findAll")
        
        # Mock Weaviate documents
        def side_effect_fetch(store, node_id):
            if node_id == "controller.ts:TestController:myEndpoint":
                return [Document(content="Controller Code", meta={"name": "myEndpoint", "type": "method", "api_method_details": '{"method": "myEndpoint", "decorator_type": "GET", "decorator_path": "/api", "base_path": "/test"}'})]
            elif node_id == "service.ts:TestService:findAll":
                return [Document(content="Service Code", meta={"name": "findAll"})]
            return []
            
        mock_fetch.side_effect = side_effect_fetch
        
        with patch.object(DocumentationCreator, '__init__', lambda self: None):
            creator = DocumentationCreator()
            creator.document_store = Mock()
            creator.generator = Mock()
            creator.output_dir = "temp"
            creator.weaviate_url = "http://fake"
            
            with patch('src.components.DocumentationCreator.get_weaviate_store') as mock_weaviate:
                # Mock the context manager to yield creator.document_store
                mock_weaviate.return_value.__enter__.return_value = creator.document_store
                
                with patch.object(LLMJsonHandler, 'parse_with_retry', return_value={"swagger": {"summary": "test"}}):
                    with patch.object(creator, '_save_outputs', return_value={"swagger": "path/file.json"}):
                        result = creator.run(endpoint_graphs={"controller.ts:TestController:myEndpoint": graph})
                        
                        assert result["methods_processed"] == 1
                        
                        # Verify `fetch_by_node_id` was queried for the controller and the service
                        assert mock_fetch.call_count == 3
                        
                        calls = [
                            call(creator.document_store, "controller.ts:TestController:myEndpoint"),
                        call(creator.document_store, "service.ts:TestService:findAll"),
                        call(creator.document_store, "controller.ts:TestController:myEndpoint")
                    ]
                    # order may not be strictly guaranteed as get_all_nodes() uses sets
                    mock_fetch.assert_has_calls(calls, any_order=True)

class TestOutputFileStructure:
    """Tests for output directory and file creation."""
    
    def test_save_outputs_creates_directory_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch.object(DocumentationCreator, '__init__', lambda self: None):
                creator = DocumentationCreator()
                creator.output_dir = tmpdir
                
                documentation = {
                    "swagger": {"summary": "Test endpoint", "responses": {}}
                }
                
                saved = creator._save_outputs("testMethod", documentation)
                
                method_dir = os.path.join(tmpdir, "testMethod")
                assert os.path.isdir(method_dir)
                assert os.path.exists(saved["swagger"])
                
                with open(saved["swagger"]) as f:
                    swagger_data = json.load(f)
                    assert swagger_data["summary"] == "Test endpoint"

class TestWeaviateFilterQuery:
    """Test fetch_by_node_id utility."""
    def test_fetch_by_node_id_filter_structure(self):
        mock_store = Mock()
        mock_store.filter_documents.return_value = []
        
        fetch_by_node_id(mock_store, "testNode:Origin:Name")
        
        mock_store.filter_documents.assert_called_once()
        call_args = mock_store.filter_documents.call_args
        filters = call_args.kwargs.get("filters") or call_args[1].get("filters")
        
        assert filters["field"] == "meta.node_id"
        assert filters["operator"] == "=="
        assert filters["value"] == "testNode:Origin:Name"
