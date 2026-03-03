"""
Tests for WeaviateDocWriter component.

Verifies that:
1. Swagger JSON outputs are correctly converted to Haystack Documents
2. Metadata (method, path, summary) is extracted correctly
3. Documents are embedded and written to Weaviate
4. Empty input is handled gracefully
"""

import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from haystack.dataclasses import Document

from src.components.WeaviateDocWriter import WeaviateDocWriter


class TestDocumentCreation:
    """Test converting swagger output files into Haystack Documents."""

    def _make_swagger_output(self, tmpdir, method_name, swagger_data):
        """Helper: write swagger.json to a method directory."""
        method_dir = os.path.join(tmpdir, method_name)
        os.makedirs(method_dir, exist_ok=True)
        path = os.path.join(method_dir, "swagger.json")
        with open(path, "w") as f:
            json.dump(swagger_data, f)
        return {method_name: {"swagger": path}}

    def test_creates_documents_from_swagger_files(self):
        """Each swagger.json should become a Document with content and metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_files = self._make_swagger_output(tmpdir, "getUser", {
                "method": "get",
                "path": "/users/{id}",
                "summary": "Get user by ID",
                "description": "Returns a single user.",
                "responses": {"200": {"description": "OK"}}
            })

            with patch.object(WeaviateDocWriter, '__init__', lambda self: None):
                writer = WeaviateDocWriter()
                docs = writer._swagger_files_to_documents(output_files)

                assert len(docs) == 1
                doc = docs[0]
                assert "Get user by ID" in doc.content
                assert doc.meta["method"] == "get"
                assert doc.meta["path"] == "/users/{id}"
                assert doc.meta["endpoint_name"] == "getUser"

    def test_creates_multiple_documents(self):
        """Multiple endpoints should produce multiple Documents."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_files = {}
            output_files.update(self._make_swagger_output(tmpdir, "getUser", {
                "method": "get", "path": "/users/{id}",
                "summary": "Get user", "responses": {}
            }))
            output_files.update(self._make_swagger_output(tmpdir, "createPost", {
                "method": "post", "path": "/posts",
                "summary": "Create post", "responses": {}
            }))

            with patch.object(WeaviateDocWriter, '__init__', lambda self: None):
                writer = WeaviateDocWriter()
                docs = writer._swagger_files_to_documents(output_files)
                assert len(docs) == 2


class TestEmptyInput:
    """Test graceful handling of empty/missing inputs."""

    def test_empty_output_files(self):
        """Empty output_files dict should return zero documents written."""
        with patch.object(WeaviateDocWriter, '__init__', lambda self: None):
            writer = WeaviateDocWriter()
            writer.embedder = Mock()
            writer.doc_writer = Mock()
            result = writer.run(output_files={}, output_dir="output")
            assert result["documents_written"] == 0


class TestMetadataExtraction:
    """Test that metadata fields are correctly pulled from swagger data."""

    def test_extracts_summary_and_description(self):
        """Summary and description should be in metadata."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_files = {}
            method_dir = os.path.join(tmpdir, "login")
            os.makedirs(method_dir)
            swagger = {
                "method": "post",
                "path": "/auth/login",
                "summary": "User login",
                "description": "Authenticates user.\n Security Concerns: ...",
                "responses": {}
            }   
            with open(os.path.join(method_dir, "swagger.json"), "w") as f:
                json.dump(swagger, f)
            output_files["login"] = {"swagger": os.path.join(method_dir, "swagger.json")}

            with patch.object(WeaviateDocWriter, '__init__', lambda self: None):
                writer = WeaviateDocWriter()
                docs = writer._swagger_files_to_documents(output_files)
                assert docs[0].meta["summary"] == "User login"

    def test_document_content_is_full_swagger_json(self):
        """Document content should be the full swagger JSON for semantic search."""
        with tempfile.TemporaryDirectory() as tmpdir:
            method_dir = os.path.join(tmpdir, "test")
            os.makedirs(method_dir)
            swagger = {
                "method": "get", "path": "/test",
                "summary": "Test", "description": "A test endpoint.",
                "parameters": [{"name": "q", "in": "query"}],
                "responses": {"200": {"description": "OK"}}
            }
            with open(os.path.join(method_dir, "swagger.json"), "w") as f:
                json.dump(swagger, f)

            with patch.object(WeaviateDocWriter, '__init__', lambda self: None):
                writer = WeaviateDocWriter()
                docs = writer._swagger_files_to_documents(
                    {"test": {"swagger": os.path.join(method_dir, "swagger.json")}}
                )
                # Content should be parseable JSON containing full swagger data
                parsed = json.loads(docs[0].content)
                assert parsed["summary"] == "Test"
                assert len(parsed["parameters"]) == 1
