import pytest
import os
import json
from unittest.mock import MagicMock, patch
from src.components.DocumentationMerger import DocumentationMerger
from haystack import Document

class TestDocumentationMerger:
    def test_merge_from_weaviate(self, tmp_path):
        """Test that merger correctly fetches and formats Swagger from Weaviate."""
        with patch("src.components.DocumentationMerger.load_config") as mock_load, \
             patch("src.components.DocumentationMerger.WeaviateStore") as mock_store_class:
            
            mock_load.return_value = {
                "doc_merger": {
                    "api_title": "Test Title",
                    "api_version": "2.0.0",
                    "api_description": "Test Desc"
                },
                "doc_creator": {
                    "output_dir": str(tmp_path)
                }
            }
            
            mock_store = MagicMock()
            mock_store_class.get_store.return_value = mock_store
            
            # Mock Documents in Weaviate
            docs = [
                Document(
                    content="doc1",
                    meta={
                        "endpoint_name": "get_user",
                        "method": "get",
                        "raw_json": json.dumps({
                            "summary": "Get User",
                            "parameters": [],
                            "responses": {}
                        })
                    }
                ),
                Document(
                    content="doc2",
                    meta={
                        "endpoint_name": "post_user",
                        "method": "post",
                        "raw_json": json.dumps({
                            "summary": "Post User",
                            "parameters": [],
                            "responses": {}
                        })
                    }
                )
            ]
            mock_store.filter_documents.return_value = docs
            
            merger = DocumentationMerger()
            result = merger.run(project_name="test_proj", output_dir=str(tmp_path))
            
            assert result["endpoints_merged"] == 2
            assert os.path.exists(result["swagger_path"])
            
            with open(result["swagger_path"], "r") as f:
                swagger = json.load(f)
                assert swagger["info"]["title"] == "Test Title"
                assert len(swagger["paths"]) == 2

    def test_merge_with_filtering(self, tmp_path):
        """Test that filtering by api_details is passed to Weaviate."""
        with patch("src.components.DocumentationMerger.load_config") as mock_load, \
             patch("src.components.DocumentationMerger.WeaviateStore") as mock_store_class:
            
            mock_load.return_value = {"doc_creator": {"output_dir": str(tmp_path)}}
            mock_store = MagicMock()
            mock_store_class.get_store.return_value = mock_store
            mock_store.filter_documents.return_value = []
            
            merger = DocumentationMerger()
            api_details = {"team_id": "team123"}
            merger.run(project_name="test_proj", api_details=api_details)
            
            # Check if filter was called with team_id
            args, kwargs = mock_store.filter_documents.call_args
            filters = kwargs["filters"]
            team_condition = next(c for c in filters["conditions"] if c["field"] == "meta.team_id")
            assert team_condition["value"] == "team123"
