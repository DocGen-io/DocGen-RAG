"""
Tests for FetchExampleGenerator component.

Verifies that:
1. Prompt is built with all endpoint details (method, path, params, body)
2. LLM response with code examples is correctly parsed
3. Empty/missing parameters are handled gracefully
4. Examples are generated for multiple frameworks
"""

import pytest
import json
from unittest.mock import Mock, patch

from src.components.FetchExampleGenerator import FetchExampleGenerator


class TestPromptBuilding:
    """Test that prompts include all endpoint details."""

    def test_prompt_includes_method_and_path(self):
        """Prompt should contain the HTTP method and full path."""
        with patch.object(FetchExampleGenerator, '__init__', lambda self: None):
            gen = FetchExampleGenerator()
            swagger = {
                "method": "post",
                "path": "/users",
                "summary": "Create user",
                "parameters": [],
                "responses": {}
            }
            prompt = gen._build_prompt(swagger)
            assert "post" in prompt.lower()
            assert "/users" in prompt

    def test_prompt_includes_parameters(self):
        """Query/path params should be in the prompt."""
        with patch.object(FetchExampleGenerator, '__init__', lambda self: None):
            gen = FetchExampleGenerator()
            swagger = {
                "method": "get",
                "path": "/users/{id}",
                "summary": "Get user",
                "parameters": [
                    {"name": "id", "in": "path", "schema": {"type": "string"}},
                    {"name": "fields", "in": "query", "schema": {"type": "string"}}
                ],
                "responses": {}
            }
            prompt = gen._build_prompt(swagger)
            assert "id" in prompt
            assert "fields" in prompt

    def test_prompt_includes_request_body(self):
        """Request body schema should be in the prompt."""
        with patch.object(FetchExampleGenerator, '__init__', lambda self: None):
            gen = FetchExampleGenerator()
            swagger = {
                "method": "post",
                "path": "/users",
                "summary": "Create user",
                "parameters": [],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "email": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "responses": {}
            }
            prompt = gen._build_prompt(swagger)
            assert "name" in prompt
            assert "email" in prompt


class TestResponseParsing:
    """Test parsing of LLM-generated code examples."""

    def test_parses_examples_for_multiple_frameworks(self):
        """Should return examples keyed by framework name."""
        with patch.object(FetchExampleGenerator, '__init__', lambda self: None):
            gen = FetchExampleGenerator()
            gen.generator = Mock()
            gen.generator.run.return_value = {
                "replies": [json.dumps({
                    "javascript": "fetch('/users')...",
                    "python": "requests.get('/users')...",
                    "curl": "curl -X GET /users"
                })]
            }

            result = gen.run(swagger_data={
                "method": "get", "path": "/users",
                "summary": "Get users", "parameters": [], "responses": {}
            })
            assert "javascript" in result["examples"]
            assert "python" in result["examples"]
            assert "curl" in result["examples"]


class TestEmptyInput:
    """Test handling of missing or empty data."""

    def test_empty_swagger_returns_empty_examples(self):
        """Empty swagger data should return empty examples."""
        with patch.object(FetchExampleGenerator, '__init__', lambda self: None):
            gen = FetchExampleGenerator()
            gen.generator = Mock()
            result = gen.run(swagger_data={})
            assert result["examples"] == {}

    def test_missing_parameters_still_builds_prompt(self):
        """Swagger without parameters should still produce a valid prompt."""
        with patch.object(FetchExampleGenerator, '__init__', lambda self: None):
            gen = FetchExampleGenerator()
            swagger = {
                "method": "get",
                "path": "/health",
                "summary": "Health check",
                "responses": {"200": {"description": "OK"}}
            }
            prompt = gen._build_prompt(swagger)
            assert "/health" in prompt
            assert "get" in prompt.lower()
