"""
Tests for EndpointClusterer component.

Verifies that:
1. K-means clustering groups endpoint embeddings correctly
2. Auto cluster count estimation works
3. Empty input is handled gracefully
4. Output structure contains cluster_id -> endpoint list mapping
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch

from src.components.EndpointClusterer import EndpointClusterer


class TestClustering:
    """Test K-means clustering on endpoint embeddings."""

    def test_clusters_endpoints_by_embeddings(self):
        """Endpoints with similar embeddings should be in the same cluster."""
        with patch.object(EndpointClusterer, '__init__', lambda self: None):
            clusterer = EndpointClusterer()

            # 4 endpoints: 2 "user" related (similar vectors), 2 "payment" related
            endpoints = [
                {"name": "getUser", "path": "/users/{id}", "summary": "Get user"},
                {"name": "createUser", "path": "/users", "summary": "Create user"},
                {"name": "getPayment", "path": "/payments/{id}", "summary": "Get payment"},
                {"name": "createPayment", "path": "/payments", "summary": "Pay"},
            ]
            embeddings = np.array([
                [1.0, 0.0, 0.0],  # user cluster
                [0.9, 0.1, 0.0],  # user cluster
                [0.0, 0.0, 1.0],  # payment cluster
                [0.1, 0.0, 0.9],  # payment cluster
            ])

            result = clusterer._cluster(endpoints, embeddings, n_clusters=2)

            assert len(result) == 2
            # Each cluster should have 2 endpoints
            sizes = sorted([len(v) for v in result.values()])
            assert sizes == [2, 2]

    def test_single_endpoint_returns_one_cluster(self):
        """Single endpoint should produce one cluster."""
        with patch.object(EndpointClusterer, '__init__', lambda self: None):
            clusterer = EndpointClusterer()
            endpoints = [{"name": "getUser", "path": "/users", "summary": "Get user"}]
            embeddings = np.array([[1.0, 0.0, 0.0]])
            result = clusterer._cluster(endpoints, embeddings, n_clusters=1)
            assert len(result) == 1
            assert len(list(result.values())[0]) == 1


class TestEmptyInput:
    """Test handling of empty or missing data."""

    def test_empty_endpoints_returns_empty(self):
        """No endpoints should return empty clusters dict."""
        with patch.object(EndpointClusterer, '__init__', lambda self: None):
            clusterer = EndpointClusterer()
            result = clusterer._cluster([], np.array([]), n_clusters=2)
            assert result == {}


class TestAutoClusterCount:
    """Test automatic cluster count estimation."""

    def test_auto_estimate_returns_reasonable_count(self):
        """Auto estimation logic should return valid n_clusters."""
        with patch.object(EndpointClusterer, '__init__', lambda self: None):
            clusterer = EndpointClusterer()
            # Test via the _cluster method which now handles the estimation
            endpoints = [{"name": f"ep{i}", "path": f"/p{i}", "summary": "s"} for i in range(5)]
            embeddings = np.random.rand(5, 10)
            
            # This should trigger the auto block
            result = clusterer._cluster(endpoints, embeddings, n_clusters=None)
            assert 1 <= len(result) <= 5

    def test_auto_estimate_for_small_input(self):
        """For very few endpoints, should return 1 or 2 clusters."""
        with patch.object(EndpointClusterer, '__init__', lambda self: None):
            clusterer = EndpointClusterer()
            
            # 1 endpoint
            res1 = clusterer._cluster([{"p": "/1", "m":"g", "s":""}], np.array([[1.0]]), n_clusters=None)
            assert len(res1) == 1
            
            # 2 endpoints
            res2 = clusterer._cluster(
                [{"p": "/1", "m":"g", "s":""}, {"p": "/2", "m":"g", "s":""}],
                np.array([[1.0, 0.0], [0.0, 1.0]]),
                n_clusters=None
            )
            assert len(res2) <= 2


class TestOutputStructure:
    """Test the output structure of clusters."""

    def test_cluster_values_contain_endpoint_info(self):
        """Each cluster entry should have endpoint name, path, summary."""
        with patch.object(EndpointClusterer, '__init__', lambda self: None):
            clusterer = EndpointClusterer()
            endpoints = [
                {"name": "getUser", "path": "/users", "summary": "Get user"},
                {"name": "getPost", "path": "/posts", "summary": "Get post"},
            ]
            embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
            result = clusterer._cluster(endpoints, embeddings, n_clusters=2)

            for cluster_id, items in result.items():
                for item in items:
                    assert "name" in item
                    assert "path" in item
