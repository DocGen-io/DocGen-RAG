"""
Unit tests for DocumentationCreator component.
"""

import pytest
import json
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from haystack.dataclasses import Document


class TestDocumentationCreatorFiltering:
    """Tests for API method filtering logic."""
    
    def test_filter_api_methods_returns_only_api_routes(self):
        """Verify only methods with is_api_route=true are returned."""
        from src.utils.json_loader import flatten_ast_methods
        
        ast_data = [{
            "file_name": "test.controller.ts.json",
            "data": [{
                "class_name": "TestController",
                "class_type": "Controller",
                "base_path": "/api",
                "methods": [
                    {
                        "method_name": "constructor",
                        "is_api_route": False,
                        "method_definition": "constructor() {}"
                    },
                    {
                        "method_name": "getAll",
                        "is_api_route": True,
                        "method_type": "Get",
                        "method_path": "",
                        "method_definition": "getAll() { return []; }"
                    },
                    {
                        "method_name": "helperMethod",
                        "is_api_route": False,
                        "method_definition": "helperMethod() {}"
                    },
                    {
                        "method_name": "getById",
                        "is_api_route": True,
                        "method_type": "Get",
                        "method_path": ":id",
                        "method_definition": "getById(id) { return {}; }"
                    }
                ]
            }]
        }]
        
        all_methods = flatten_ast_methods(ast_data)
        api_methods = [m for m in all_methods if m.get("is_api_route") is True]
        
        assert len(api_methods) == 2
        assert api_methods[0]["method_name"] == "getAll"
        assert api_methods[1]["method_name"] == "getById"
    
    def test_filter_api_methods_with_no_api_routes(self):
        """Verify empty list when no API routes exist."""
        from src.utils.json_loader import flatten_ast_methods
        
        ast_data = [{
            "file_name": "service.ts.json",
            "data": [{
                "class_name": "TestService",
                "methods": [
                    {
                        "method_name": "doSomething",
                        "is_api_route": False,
                        "method_definition": "doSomething() {}"
                    }
                ]
            }]
        }]
        
        all_methods = flatten_ast_methods(ast_data)
        api_methods = [m for m in all_methods if m.get("is_api_route") is True]
        
        assert len(api_methods) == 0


class TestWeaviateFilterQuery:
    """Tests for Weaviate filter construction."""
    
    def test_fetch_by_method_name_filter_structure(self):
        """Verify correct filter structure for exact method name match."""
        from src.utils.weaviate_utils import fetch_by_method_name
        
        mock_store = Mock()
        mock_store.filter_documents.return_value = []
        
        fetch_by_method_name(mock_store, "findById")
        
        # Check the filter was called with correct structure
        mock_store.filter_documents.assert_called_once()
        call_args = mock_store.filter_documents.call_args
        filters = call_args.kwargs.get("filters") or call_args[1].get("filters")
        
        assert filters["operator"] == "AND"
        assert len(filters["conditions"]) == 2
        
        # Check type condition
        type_condition = filters["conditions"][0]
        assert type_condition["field"] == "meta.type"
        assert type_condition["operator"] == "=="
        assert type_condition["value"] == "ast_method"
        
        # Check method_name condition
        name_condition = filters["conditions"][1]
        assert name_condition["field"] == "meta.method_name"
        assert name_condition["operator"] == "=="
        assert name_condition["value"] == "findById"
    
    def test_fetch_by_method_name_returns_documents(self):
        """Verify documents are returned from Weaviate query."""
        from src.utils.weaviate_utils import fetch_by_method_name
        
        mock_doc = Document(content="test content", meta={"method_name": "findById"})
        mock_store = Mock()
        mock_store.filter_documents.return_value = [mock_doc]
        
        result = fetch_by_method_name(mock_store, "findById")
        
        assert len(result) == 1
        assert result[0].content == "test content"


class TestOutputFileStructure:
    """Tests for output directory and file creation."""
    
    def test_save_outputs_creates_directory_structure(self):
        """Verify correct directory and file creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.components.DocumentationCreator import DocumentationCreator
            
            # Mock the component initialization
            with patch.object(DocumentationCreator, '__init__', lambda self: None):
                creator = DocumentationCreator()
                creator.output_dir = tmpdir
                
                documentation = {
                    "postman": {"name": "Test Endpoint", "method": "GET"},
                    "swagger": {"summary": "Test endpoint", "responses": {}}
                }
                
                saved = creator._save_outputs("testMethod", documentation)
                
                # Check directory was created
                method_dir = os.path.join(tmpdir, "testMethod")
                assert os.path.isdir(method_dir)
                
                # Check files were created
                assert os.path.exists(saved["postman"])
                assert os.path.exists(saved["swagger"])
                
                # Verify JSON content
                with open(saved["postman"]) as f:
                    postman_data = json.load(f)
                    assert postman_data["name"] == "Test Endpoint"
                
                with open(saved["swagger"]) as f:
                    swagger_data = json.load(f)
                    assert swagger_data["summary"] == "Test endpoint"


class TestJsonFormat:
    """Tests for valid JSON output format."""
    
    def test_postman_json_is_valid(self):
        """Verify Postman output is valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.components.DocumentationCreator import DocumentationCreator
            
            with patch.object(DocumentationCreator, '__init__', lambda self: None):
                creator = DocumentationCreator()
                creator.output_dir = tmpdir
                
                documentation = {
                    "postman": {
                        "name": "Get All Posts",
                        "request": {
                            "method": "GET",
                            "header": [],
                            "url": {"raw": "{{baseUrl}}/posts"}
                        }
                    },
                    "swagger": {}
                }
                
                saved = creator._save_outputs("getAllPosts", documentation)
                
                # Should not raise JSONDecodeError
                with open(saved["postman"]) as f:
                    data = json.load(f)
                    assert "name" in data
    
    def test_swagger_json_is_valid_openapi_structure(self):
        """Verify Swagger output has OpenAPI-like structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from src.components.DocumentationCreator import DocumentationCreator
            
            with patch.object(DocumentationCreator, '__init__', lambda self: None):
                creator = DocumentationCreator()
                creator.output_dir = tmpdir
                
                documentation = {
                    "postman": {},
                    "swagger": {
                        "summary": "Get all posts",
                        "description": "Retrieves all blog posts",
                        "parameters": [],
                        "responses": {
                            "200": {"description": "Success"}
                        }
                    }
                }
                
                saved = creator._save_outputs("getAllPosts", documentation)
                
                with open(saved["swagger"]) as f:
                    data = json.load(f)
                    assert "summary" in data
                    assert "responses" in data


class TestGetDependenciesForMethod:
    """Tests for dependency extraction from mapped_ast."""
    
    def test_get_dependencies_returns_correct_list(self):
        """Verify correct dependencies are extracted for a method."""
        from src.components.DocumentationCreator import DocumentationCreator
        
        with patch.object(DocumentationCreator, '__init__', lambda self: None):
            creator = DocumentationCreator()
            
            mapped_ast = {
                "PostController": {
                    "methods": [
                        {"method": "getAllPosts", "dependencies": ["postService.findAll"]},
                        {"method": "getPostById", "dependencies": ["postService.findById"]}
                    ]
                }
            }
            
            deps = creator._get_dependencies_for_method("PostController", "getAllPosts", mapped_ast)
            
            assert deps == ["postService.findAll"]
    
    def test_get_dependencies_returns_empty_for_missing_method(self):
        """Verify empty list for non-existent method."""
        from src.components.DocumentationCreator import DocumentationCreator
        
        with patch.object(DocumentationCreator, '__init__', lambda self: None):
            creator = DocumentationCreator()
            
            mapped_ast = {"SomeController": {"methods": []}}
            
            deps = creator._get_dependencies_for_method("PostController", "unknownMethod", mapped_ast)
            
            assert deps == []
