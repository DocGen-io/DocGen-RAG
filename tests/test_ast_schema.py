"""
Tests for AST Schema validation.

Ensures all language extractors produce consistent output format.
"""

import pytest
import json
import os
from pydantic import ValidationError

from src.utils.ast_schema import ASTMethodSchema, ASTClassSchema, validate_ast_output


class TestASTMethodSchema:
    """Tests for method schema validation."""
    
    def test_valid_api_method(self):
        """Valid API method should pass validation."""
        data = {
            "method_name": "getUsers",
            "method_type": "Get",
            "is_api_route": True,
            "method_path": "/users",
            "method_definition": "getUsers() { return []; }"
        }
        method = ASTMethodSchema(**data)
        assert method.method_name == "getUsers"
        assert method.is_api_route is True
    
    def test_valid_non_api_method(self):
        """Non-API method with null types should pass."""
        data = {
            "method_name": "helperMethod",
            "method_type": None,
            "is_api_route": False,
            "method_path": None,
            "method_definition": "helperMethod() {}"
        }
        method = ASTMethodSchema(**data)
        assert method.is_api_route is False
    
    def test_missing_method_name_fails(self):
        """Missing method_name should fail validation."""
        data = {
            "method_type": "Get",
            "is_api_route": True,
            "method_path": "/",
            "method_definition": "() {}"
        }
        with pytest.raises(ValidationError):
            ASTMethodSchema(**data)
    
    def test_empty_method_name_fails(self):
        """Empty method_name should fail validation."""
        data = {
            "method_name": "",
            "method_type": "Get",
            "is_api_route": True,
            "method_path": "/",
            "method_definition": "() {}"
        }
        with pytest.raises(ValidationError):
            ASTMethodSchema(**data)
    
    def test_missing_is_api_route_fails(self):
        """Missing is_api_route should fail validation."""
        data = {
            "method_name": "test",
            "method_type": "Get",
            "method_path": "/",
            "method_definition": "test() {}"
        }
        with pytest.raises(ValidationError):
            ASTMethodSchema(**data)


class TestASTClassSchema:
    """Tests for class schema validation."""
    
    def test_valid_controller_class(self):
        """Valid controller class should pass validation."""
        data = {
            "class_name": "UserController",
            "class_type": "Controller",
            "base_path": "/api/users",
            "methods": [
                {
                    "method_name": "getAll",
                    "method_type": "Get",
                    "is_api_route": True,
                    "method_path": "",
                    "method_definition": "getAll() {}"
                }
            ]
        }
        cls = ASTClassSchema(**data)
        assert cls.class_name == "UserController"
        assert len(cls.methods) == 1
    
    def test_function_based_module_without_class(self):
        """Function-based modules (like FastAPI) can have no class_name."""
        data = {
            "class_name": None,
            "base_path": "/api",
            "methods": [
                {
                    "method_name": "get_users",
                    "method_type": "Get",
                    "is_api_route": True,
                    "method_path": "/users",
                    "method_definition": "def get_users(): pass"
                }
            ]
        }
        cls = ASTClassSchema(**data)
        assert cls.class_name is None
        assert len(cls.methods) == 1
    
    def test_default_base_path(self):
        """Missing base_path should default to /."""
        data = {
            "class_name": "TestClass",
            "methods": []
        }
        cls = ASTClassSchema(**data)
        assert cls.base_path == "/"


class TestValidateASTOutput:
    """Tests for full AST output validation."""
    
    def test_validate_complete_ast_output(self):
        """Complete AST output should validate successfully."""
        data = [
            {
                "class_name": "PostController",
                "class_type": "Controller",
                "base_path": "/posts",
                "methods": [
                    {
                        "method_name": "constructor",
                        "method_type": None,
                        "is_api_route": False,
                        "method_path": None,
                        "method_definition": "constructor() {}"
                    },
                    {
                        "method_name": "getAllPosts",
                        "method_type": "Get",
                        "is_api_route": True,
                        "method_path": "",
                        "method_definition": "getAllPosts() { return []; }"
                    }
                ]
            }
        ]
        result = validate_ast_output(data)
        assert len(result) == 1
        assert result[0].class_name == "PostController"
        assert len(result[0].methods) == 2


class TestRealASTFiles:
    """Test validation against real AST files in the project."""
    
    @pytest.fixture
    def ast_folder(self):
        return "ast"
    
    def test_all_ast_files_conform_to_schema(self, ast_folder):
        """All JSON files in ast folder should match the schema."""
        if not os.path.exists(ast_folder):
            pytest.skip("AST folder not found")
        
        for filename in os.listdir(ast_folder):
            if not filename.endswith('.json'):
                continue
            
            filepath = os.path.join(ast_folder, filename)
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Validate each file
            try:
                result = validate_ast_output(data)
                assert len(result) > 0, f"{filename} has no classes"
            except ValidationError as e:
                pytest.fail(f"{filename} failed validation: {e}")
