"""
Tests for SwaggerBuilder schema normalization:
- Opaque DTO response schemas should be marked x-uncertain: true (not stripped)
- Object-type query params with no properties should be dropped
"""

import pytest
from src.utils.output_format_builders.swagger_builder import SwaggerBuilder


@pytest.fixture
def builder():
    return SwaggerBuilder()


class TestOpaqueDtoResponse:
    """
    When LLM inlines a $ref as {"type": "object", "description": "Object of type XxxDto"},
    we want x-uncertain: true added — so the user sees the DTO name but knows it's unresolved.
    """

    def test_opaque_ref_schema_gets_uncertain_flag(self, builder):
        """$ref-inlined opaque DTO in response must carry x-uncertain: true."""
        schema = {"type": "object", "description": "Object of type HeatmapResponseDto"}
        result = builder._normalize_schema(schema)
        assert result.get("x-uncertain") is True
        # The description must still be present so devs know the predicted type
        assert "HeatmapResponseDto" in result.get("description", "")

    def test_non_opaque_schema_no_uncertain_flag(self, builder):
        """A real expanded schema with properties must NOT get x-uncertain: true."""
        schema = {
            "type": "object",
            "properties": {
                "id": {"type": "integer", "example": 1},
                "name": {"type": "string", "example": "Alice"},
            }
        }
        result = builder._normalize_schema(schema)
        assert "x-uncertain" not in result

    def test_opaque_array_ref_schema_gets_uncertain_flag(self, builder):
        """$ref array is inlined as {type: array, items: {type: object, ..., x-uncertain: true}}."""
        # Simulates what _normalize_schema produces for {"$ref": "#/components/schemas/TopPlayerStatDto"}
        # when it appears inside an array items field — i.e. after the $ref branch runs.
        schema = {"$ref": "#/components/schemas/GameDto[]"}
        result = builder._normalize_schema(schema)
        # The outer type must be array with items nested inside
        assert result.get("type") == "array"
        items = result.get("items", {})
        assert items.get("x-uncertain") is True
        assert "GameDto" in items.get("description", "")


class TestObjectQueryParamStripping:
    """
    Object-type query params with no properties (opaque DTOs) should be dropped
    from the parameters list entirely — not flattened to `type: string`.
    """

    def test_object_query_param_without_properties_is_dropped(self, builder):
        """Opaque object query params (no properties) must be removed from output."""
        params = [
            {
                "name": "pagination",
                "in": "query",
                "required": False,
                "schema": {"type": "object", "description": "Object of type PaginationQueryDto"}
            }
        ]
        result = builder._normalize_parameters(params, set())
        # No `pagination` param should survive
        names = [p["name"] for p in result]
        assert "pagination" not in names

    def test_object_query_param_with_properties_is_kept(self, builder):
        """Object query params with real properties should be kept as-is."""
        params = [
            {
                "name": "filter",
                "in": "query",
                "required": False,
                "schema": {
                    "type": "object",
                    "properties": {"page": {"type": "integer"}, "limit": {"type": "integer"}}
                }
            }
        ]
        result = builder._normalize_parameters(params, set())
        names = [p["name"] for p in result]
        assert "filter" in names

    def test_primitive_query_param_is_kept(self, builder):
        """Normal primitive query params must pass through unchanged."""
        params = [
            {"name": "gameType", "in": "query", "required": False, "schema": {"type": "string"}}
        ]
        result = builder._normalize_parameters(params, set())
        assert len(result) == 1
        assert result[0]["name"] == "gameType"


class TestEmptySchemaStripping:
    """_is_empty_schema and _normalize_response should drop useless content blocks."""

    def test_empty_dict_is_empty(self, builder):
        assert builder._is_empty_schema({}) is True

    def test_only_x_uncertain_is_empty(self, builder):
        assert builder._is_empty_schema({"x-uncertain": True}) is True

    def test_array_without_items_is_empty(self, builder):
        assert builder._is_empty_schema({"type": "array"}) is True

    def test_array_with_empty_items_is_empty(self, builder):
        assert builder._is_empty_schema({"type": "array", "items": {}}) is True

    def test_array_with_uncertain_items_is_not_empty(self, builder):
        """Array with x-uncertain items still has description — keep it."""
        schema = {"type": "array", "items": {"type": "object", "description": "Object of type Foo", "x-uncertain": True}}
        assert builder._is_empty_schema(schema) is False

    def test_real_schema_is_not_empty(self, builder):
        schema = {"type": "object", "properties": {"id": {"type": "integer"}}}
        assert builder._is_empty_schema(schema) is False

    def test_normalize_response_drops_empty_schema_content(self, builder):
        """When response content schema is {}, content key must not appear."""
        r = {"description": "OK", "content": {"application/json": {"schema": {}}}}
        result = builder._normalize_response(r)
        assert "content" not in result
        assert result["description"] == "OK"

    def test_normalize_response_keeps_content_with_real_schema(self, builder):
        """Response with real properties must keep content."""
        r = {
            "description": "OK",
            "content": {"application/json": {"schema": {
                "type": "object",
                "properties": {"id": {"type": "integer", "example": 1}}
            }}}
        }
        result = builder._normalize_response(r)
        assert "content" in result

    def test_normalize_response_keeps_uncertain_array_items(self, builder):
        """Response with array of uncertain DTO items should KEEP content (DTO name is useful)."""
        r = {
            "description": "OK",
            "content": {"application/json": {"schema": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/TopPlayerStatDto"}
            }}}
        }
        result = builder._normalize_response(r)
        # Should still have content because the DTO name is shown
        assert "content" in result
        items = result["content"]["application/json"]["schema"].get("items", {})
        assert "TopPlayerStatDto" in items.get("description", "")


class TestTrailingSlashNormalization:
    """Trailing slashes should be stripped to prevent /users/ vs /users duplicates."""

    def test_trailing_slash_stripped(self, builder):
        assert builder._normalize_path("/users/") == "/users"

    def test_root_slash_preserved(self, builder):
        assert builder._normalize_path("/") == "/"

    def test_no_trailing_slash_unchanged(self, builder):
        assert builder._normalize_path("/users") == "/users"

    def test_trailing_slash_with_params(self, builder):
        assert builder._normalize_path("/articles/:slug/") == "/articles/{slug}"

    def test_duplicate_paths_deduplicated_in_build(self, builder):
        """Two endpoints with /users and /users/ should merge into one path."""
        endpoints = [
            {"http_method": "GET", "method_name": "listUsers", "data": {"path": "/users", "summary": "List users", "responses": {"200": {"description": "OK"}}}},
            {"http_method": "POST", "method_name": "createUser", "data": {"path": "/users/", "summary": "Create user", "responses": {"201": {"description": "Created"}}}},
        ]
        spec = builder.build(endpoints)
        assert "/users" in spec["paths"]
        assert "/users/" not in spec["paths"]
        assert "get" in spec["paths"]["/users"]
        assert "post" in spec["paths"]["/users"]
